"""
Views do app TMS — ViewSets DRF com actions de ciclo de vida.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import audit
from .models import (
    Veiculo, Motorista,
    Romaneio, ItemRomaneio,
    Ocorrencia, POD,
    StatusRomaneio,
)
from .serializers import (
    VeiculoSerializer, MotoristaSerializer,
    RomaneioSerializer, RomaneioListSerializer,
    ItemRomaneioSerializer,
    OcorrenciaSerializer, PODSerializer,
)


# ─── Veículo ──────────────────────────────────────────────────────────────────

class VeiculoViewSet(viewsets.ModelViewSet):
    serializer_class   = VeiculoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Veiculo.objects.para_request(self.request)

        status_filtro = self.request.query_params.get("status")
        if status_filtro:
            qs = qs.filter(status=status_filtro)

        tipo_filtro = self.request.query_params.get("tipo")
        if tipo_filtro:
            qs = qs.filter(tipo=tipo_filtro)

        apenas_ativos = self.request.query_params.get("ativo")
        if apenas_ativos is not None:
            qs = qs.filter(ativo=apenas_ativos.lower() in ("true", "1", "yes"))

        return qs

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)


# ─── Motorista ────────────────────────────────────────────────────────────────

class MotoristaViewSet(viewsets.ModelViewSet):
    serializer_class   = MotoristaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Motorista.objects.para_request(self.request)

        apenas_ativos = self.request.query_params.get("ativo")
        if apenas_ativos is not None:
            qs = qs.filter(ativo=apenas_ativos.lower() in ("true", "1", "yes"))

        return qs

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)


# ─── Romaneio ─────────────────────────────────────────────────────────────────

class RomaneioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return RomaneioListSerializer
        return RomaneioSerializer

    def get_queryset(self):
        qs = Romaneio.objects.para_request(self.request).select_related(
            "veiculo", "motorista", "responsavel"
        )

        status_filtro = self.request.query_params.get("status")
        if status_filtro:
            qs = qs.filter(status=status_filtro)

        motorista_id = self.request.query_params.get("motorista")
        if motorista_id:
            qs = qs.filter(motorista_id=motorista_id)

        veiculo_id = self.request.query_params.get("veiculo")
        if veiculo_id:
            qs = qs.filter(veiculo_id=veiculo_id)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            empresa=self.request.user.empresa,
            responsavel=self.request.user,
        )

    # ── Actions de ciclo de vida ──────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="iniciar-rota")
    def iniciar_rota(self, request, pk=None):
        """
        POST /api/tms/romaneios/<id>/iniciar-rota/
        Inicia a rota: status aberto → em_rota.
        """
        romaneio = self.get_object()

        try:
            romaneio.iniciar_rota(usuario=request.user)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit(
            request.user, "tms", "romaneio.iniciar_rota",
            "Romaneio", objeto_id=romaneio.id,
            payload_depois={"status": romaneio.status, "numero": romaneio.numero},
        )

        return Response(RomaneioSerializer(romaneio, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="concluir")
    def concluir(self, request, pk=None):
        """
        POST /api/tms/romaneios/<id>/concluir/
        Conclui o romaneio: em_rota | com_ocorrencia → concluido.
        """
        romaneio = self.get_object()

        try:
            romaneio.concluir(usuario=request.user)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit(
            request.user, "tms", "romaneio.concluir",
            "Romaneio", objeto_id=romaneio.id,
            payload_depois={"status": romaneio.status, "numero": romaneio.numero},
        )

        return Response(RomaneioSerializer(romaneio, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        """
        POST /api/tms/romaneios/<id>/cancelar/
        Cancela o romaneio.
        """
        romaneio = self.get_object()

        try:
            romaneio.cancelar(usuario=request.user)
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        audit(
            request.user, "tms", "romaneio.cancelar",
            "Romaneio", objeto_id=romaneio.id,
            payload_depois={"status": romaneio.status},
        )

        return Response(RomaneioSerializer(romaneio, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="ocorrencias")
    def listar_ocorrencias(self, request, pk=None):
        """
        GET /api/tms/romaneios/<id>/ocorrencias/
        Lista todas as ocorrências do romaneio.
        """
        romaneio = self.get_object()
        qs       = romaneio.ocorrencias.select_related("registrado_por", "item").all()
        serializer = OcorrenciaSerializer(qs, many=True)
        return Response(serializer.data)


# ─── Item de Romaneio ─────────────────────────────────────────────────────────

class ItemRomaneioViewSet(viewsets.ModelViewSet):
    """
    ViewSet de itens. Filtrar por romaneio via ?romaneio=<uuid>.
    """
    serializer_class   = ItemRomaneioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ItemRomaneio.objects.select_related(
            "romaneio", "saida_wms"
        ).filter(romaneio__empresa=self.request.user.empresa)

        romaneio_id = self.request.query_params.get("romaneio")
        if romaneio_id:
            qs = qs.filter(romaneio_id=romaneio_id)

        status_entrega = self.request.query_params.get("status_entrega")
        if status_entrega:
            qs = qs.filter(status_entrega=status_entrega)

        return qs.order_by("romaneio", "ordem_entrega")


# ─── Ocorrência ───────────────────────────────────────────────────────────────

class OcorrenciaViewSet(viewsets.ModelViewSet):
    """
    Criação e leitura de ocorrências.
    Filtrar por romaneio via ?romaneio=<uuid>.
    """
    serializer_class   = OcorrenciaSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "head", "options"]  # sem PUT/PATCH/DELETE

    def get_queryset(self):
        qs = Ocorrencia.objects.select_related(
            "romaneio", "item", "registrado_por"
        ).filter(romaneio__empresa=self.request.user.empresa)

        romaneio_id = self.request.query_params.get("romaneio")
        if romaneio_id:
            qs = qs.filter(romaneio_id=romaneio_id)

        tipo_filtro = self.request.query_params.get("tipo")
        if tipo_filtro:
            qs = qs.filter(tipo=tipo_filtro)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)


# ─── POD — Proof of Delivery ──────────────────────────────────────────────────

class PODViewSet(viewsets.ModelViewSet):
    """
    Comprovantes de entrega — criação + leitura; sem edição (imutável).
    Filtrar por item via ?item=<uuid>.
    """
    serializer_class   = PODSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ["get", "post", "head", "options"]  # sem PUT/PATCH/DELETE

    def get_queryset(self):
        qs = POD.objects.select_related(
            "item__romaneio"
        ).filter(item__romaneio__empresa=self.request.user.empresa)

        item_id = self.request.query_params.get("item")
        if item_id:
            qs = qs.filter(item_id=item_id)

        romaneio_id = self.request.query_params.get("romaneio")
        if romaneio_id:
            qs = qs.filter(item__romaneio_id=romaneio_id)

        return qs.order_by("-created_at")
