"""
Views do app CRM — ViewSets DRF com actions de funil de vendas.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import audit
from .models import (
    Cliente, Contato,
    Oportunidade, HistoricoInteracao, Contrato,
    StatusCliente,
)
from .serializers import (
    ClienteSerializer, ClienteListSerializer,
    ContatoSerializer,
    OportunidadeSerializer,
    HistoricoInteracaoSerializer,
    ContratoSerializer,
)


# ─── Cliente ──────────────────────────────────────────────────────────────────

class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ClienteListSerializer
        return ClienteSerializer

    def get_queryset(self):
        qs = Cliente.objects.para_request(self.request).select_related(
            "responsavel"
        )

        status_filtro = self.request.query_params.get("status")
        if status_filtro:
            qs = qs.filter(status=status_filtro)

        segmento = self.request.query_params.get("segmento")
        if segmento:
            qs = qs.filter(segmento=segmento)

        responsavel_id = self.request.query_params.get("responsavel")
        if responsavel_id:
            qs = qs.filter(responsavel_id=responsavel_id)

        busca = self.request.query_params.get("q")
        if busca:
            qs = qs.filter(razao_social__icontains=busca) | qs.filter(nome_fantasia__icontains=busca)

        return qs.order_by("razao_social")

    def perform_create(self, serializer):
        serializer.save(
            empresa=self.request.user.empresa,
            responsavel=self.request.user,
        )

    # ── Actions de sub-recursos ──────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="contatos")
    def listar_contatos(self, request, pk=None):
        """GET /api/crm/clientes/<id>/contatos/"""
        cliente = self.get_object()
        contatos = cliente.contatos.filter(ativo=True).order_by("-decisor", "nome_completo")
        return Response(ContatoSerializer(contatos, many=True).data)

    @action(detail=True, methods=["get"], url_path="oportunidades")
    def listar_oportunidades(self, request, pk=None):
        """GET /api/crm/clientes/<id>/oportunidades/"""
        cliente = self.get_object()
        oportunidades = cliente.oportunidades.select_related("responsavel").order_by("-created_at")
        return Response(OportunidadeSerializer(oportunidades, many=True).data)

    @action(detail=True, methods=["get"], url_path="historico")
    def listar_historico(self, request, pk=None):
        """GET /api/crm/clientes/<id>/historico/"""
        cliente = self.get_object()
        historico = cliente.historico.select_related(
            "registrado_por", "contato", "oportunidade"
        ).order_by("-data_interacao")
        return Response(HistoricoInteracaoSerializer(historico, many=True).data)

    @action(detail=True, methods=["get"], url_path="contrato")
    def contrato_ativo(self, request, pk=None):
        """GET /api/crm/clientes/<id>/contrato/ — retorna o contrato ativo mais recente."""
        cliente = self.get_object()
        contrato = cliente.contratos.filter(ativo=True).order_by("-vigencia_inicio").first()
        if not contrato:
            return Response({"detalhe": "Nenhum contrato ativo."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ContratoSerializer(contrato).data)


# ─── Contato ──────────────────────────────────────────────────────────────────

class ContatoViewSet(viewsets.ModelViewSet):
    serializer_class   = ContatoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contato.objects.select_related(
            "cliente"
        ).filter(cliente__empresa=self.request.user.empresa)

        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        apenas_ativos = self.request.query_params.get("ativo")
        if apenas_ativos is not None:
            qs = qs.filter(ativo=apenas_ativos.lower() in ("true", "1", "yes"))

        decisor = self.request.query_params.get("decisor")
        if decisor is not None:
            qs = qs.filter(decisor=decisor.lower() in ("true", "1", "yes"))

        return qs.order_by("-decisor", "nome_completo")


# ─── Oportunidade ─────────────────────────────────────────────────────────────

class OportunidadeViewSet(viewsets.ModelViewSet):
    serializer_class   = OportunidadeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Oportunidade.objects.select_related(
            "cliente", "responsavel"
        ).filter(cliente__empresa=self.request.user.empresa)

        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        etapa = self.request.query_params.get("etapa")
        if etapa:
            qs = qs.filter(etapa=etapa)

        responsavel_id = self.request.query_params.get("responsavel")
        if responsavel_id:
            qs = qs.filter(responsavel_id=responsavel_id)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(responsavel=self.request.user)

    # ── Actions de funil ─────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="fechar-ganho")
    def fechar_ganho(self, request, pk=None):
        """
        POST /api/crm/oportunidades/<id>/fechar-ganho/
        Fecha como ganho e ativa o cliente.
        """
        oportunidade = self.get_object()

        try:
            oportunidade.fechar_ganho(usuario=request.user)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit(
            request.user, "crm", "oportunidade.fechar_ganho",
            "Oportunidade", objeto_id=oportunidade.id,
            payload_depois={
                "etapa": oportunidade.etapa,
                "cliente_status": oportunidade.cliente.status,
            },
        )

        return Response(OportunidadeSerializer(oportunidade, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="fechar-perdido")
    def fechar_perdido(self, request, pk=None):
        """
        POST /api/crm/oportunidades/<id>/fechar-perdido/
        Body opcional: {"motivo": "Preço acima do concorrente"}
        """
        oportunidade = self.get_object()
        motivo = request.data.get("motivo", "")

        try:
            oportunidade.fechar_perdido(motivo=motivo, usuario=request.user)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit(
            request.user, "crm", "oportunidade.fechar_perdido",
            "Oportunidade", objeto_id=oportunidade.id,
            payload_depois={"etapa": oportunidade.etapa, "motivo": motivo},
        )

        return Response(OportunidadeSerializer(oportunidade, context={"request": request}).data)


# ─── Histórico de Interação ───────────────────────────────────────────────────

class HistoricoInteracaoViewSet(viewsets.ModelViewSet):
    """
    Histórico de interações — criação e leitura apenas (imutável).
    Filtro: ?cliente= ?oportunidade= ?tipo=
    """
    serializer_class   = HistoricoInteracaoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "head", "options"]  # sem PUT/PATCH/DELETE

    def get_queryset(self):
        qs = HistoricoInteracao.objects.select_related(
            "cliente", "oportunidade", "contato", "registrado_por"
        ).filter(cliente__empresa=self.request.user.empresa)

        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        oportunidade_id = self.request.query_params.get("oportunidade")
        if oportunidade_id:
            qs = qs.filter(oportunidade_id=oportunidade_id)

        tipo = self.request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        return qs.order_by("-data_interacao")

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)


# ─── Contrato ─────────────────────────────────────────────────────────────────

class ContratoViewSet(viewsets.ModelViewSet):
    serializer_class   = ContratoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contrato.objects.select_related(
            "cliente"
        ).filter(cliente__empresa=self.request.user.empresa)

        cliente_id = self.request.query_params.get("cliente")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        apenas_ativos = self.request.query_params.get("ativo")
        if apenas_ativos is not None:
            qs = qs.filter(ativo=apenas_ativos.lower() in ("true", "1", "yes"))

        return qs.order_by("-vigencia_inicio")
