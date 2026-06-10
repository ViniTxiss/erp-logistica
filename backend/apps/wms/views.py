"""
Views do app WMS.
"""
from django.db.models import Sum, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import require_permission
from apps.core.audit import audit
from .models import (
    Armazem, Posicao, Produto,
    EntradaMercadoria, SaidaMercadoria, MovimentacaoEstoque,
)
from .serializers import (
    ArmazemSerializer, PosicaoSerializer, ProdutoSerializer,
    EntradaMercadoriaSerializer, EntradaMercadoriaListSerializer,
    SaidaMercadoriaSerializer, MovimentacaoEstoqueSerializer,
    SaldoPorPosicaoSerializer,
)


class ArmazemViewSet(viewsets.ModelViewSet):
    serializer_class = ArmazemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Armazem.objects.filter(empresa=self.request.user.empresa)


class PosicaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PosicaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Posicao.objects.select_related(
            "nivel__bay__corredor__armazem"
        ).filter(nivel__bay__corredor__armazem__empresa=self.request.user.empresa)

        armazem_id = self.request.query_params.get("armazem")
        if armazem_id:
            qs = qs.filter(nivel__bay__corredor__armazem_id=armazem_id)

        return qs

    @action(detail=False, methods=["get"], url_path="saldo")
    def saldo(self, request):
        """
        GET /api/wms/posicoes/saldo/?armazem=<uuid>
        Retorna saldo atual por posição e produto.
        """
        qs = MovimentacaoEstoque.objects.filter(
            posicao__nivel__bay__corredor__armazem__empresa=request.user.empresa
        ).values(
            posicao_codigo=F("posicao__codigo"),
            produto_sku=F("produto__sku"),
            produto_descricao=F("produto__descricao"),
        ).annotate(saldo=Sum("quantidade")).filter(saldo__gt=0)

        armazem_id = request.query_params.get("armazem")
        if armazem_id:
            qs = qs.filter(posicao__nivel__bay__corredor__armazem_id=armazem_id)

        serializer = SaldoPorPosicaoSerializer(qs, many=True)
        return Response(serializer.data)


class ProdutoViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Produto.objects.filter(empresa=self.request.user.empresa)


class EntradaMercadoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return EntradaMercadoriaListSerializer
        return EntradaMercadoriaSerializer

    def get_queryset(self):
        qs = EntradaMercadoria.objects.select_related(
            "armazem", "responsavel"
        ).filter(armazem__empresa=self.request.user.empresa)

        status_filtro = self.request.query_params.get("status")
        if status_filtro:
            qs = qs.filter(status=status_filtro)

        return qs.order_by("-chegada_em")

    @action(detail=True, methods=["post"], url_path="concluir")
    def concluir(self, request, pk=None):
        """
        POST /api/wms/entradas/<id>/concluir/
        Conclui o recebimento e gera movimentações de estoque.
        """
        entrada = self.get_object()

        if entrada.status == "concluido":
            return Response(
                {"erro": "Esta entrada já foi concluída."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrada.concluir(usuario=request.user)

        audit(
            request.user, "wms", "entrada.concluir",
            "EntradaMercadoria", objeto_id=entrada.id,
            payload_depois={"numero_nf": entrada.numero_nf},
        )

        return Response(
            EntradaMercadoriaSerializer(entrada, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="marcar-divergencia")
    def marcar_divergencia(self, request, pk=None):
        entrada = self.get_object()
        entrada.status = "divergencia"
        entrada.save(update_fields=["status", "updated_at"])
        return Response({"status": "divergencia marcada"})


class SaidaMercadoriaViewSet(viewsets.ModelViewSet):
    serializer_class = SaidaMercadoriaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SaidaMercadoria.objects.select_related(
            "armazem", "responsavel"
        ).filter(armazem__empresa=self.request.user.empresa)

    @action(detail=True, methods=["post"], url_path="expedir")
    def expedir(self, request, pk=None):
        saida = self.get_object()
        if saida.status == "expedido":
            return Response({"erro": "Já expedida."}, status=status.HTTP_400_BAD_REQUEST)
        saida.expedir(usuario=request.user)
        return Response(SaidaMercadoriaSerializer(saida, context={"request": request}).data)


class MovimentacaoEstoqueViewSet(viewsets.ReadOnlyModelViewSet):
    """Ledger de movimentações — somente leitura."""
    serializer_class = MovimentacaoEstoqueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MovimentacaoEstoque.objects.select_related(
            "posicao", "produto", "usuario"
        ).filter(posicao__nivel__bay__corredor__armazem__empresa=self.request.user.empresa)

        produto_id = self.request.query_params.get("produto")
        posicao_id = self.request.query_params.get("posicao")

        if produto_id:
            qs = qs.filter(produto_id=produto_id)
        if posicao_id:
            qs = qs.filter(posicao_id=posicao_id)

        return qs.order_by("-created_at")
