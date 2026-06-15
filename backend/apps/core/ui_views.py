from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from apps.wms.models import EntradaMercadoria, Produto
from apps.tms.models import Romaneio, Motorista, Veiculo
from apps.crm.models import Cliente, Oportunidade

@login_required(login_url="/admin/login/")
def dashboard(request):
    empresa = request.user.empresa
    
    # Base queries depending on tenant (Multi-tenant)
    if empresa:
        entradas_qs = EntradaMercadoria.objects.filter(armazem__empresa=empresa)
        produtos_qs = Produto.objects.filter(empresa=empresa)
        romaneios_qs = Romaneio.objects.filter(empresa=empresa)
        motoristas_qs = Motorista.objects.filter(empresa=empresa, ativo=True)
        veiculos_qs = Veiculo.objects.filter(empresa=empresa, ativo=True)
        clientes_qs = Cliente.objects.filter(empresa=empresa)
        oportunidades_qs = Oportunidade.objects.filter(cliente__empresa=empresa)
    else:
        # Superuser fallback / overall view across all companies
        entradas_qs = EntradaMercadoria.objects.all()
        produtos_qs = Produto.objects.all()
        romaneios_qs = Romaneio.objects.all()
        motoristas_qs = Motorista.objects.filter(ativo=True)
        veiculos_qs = Veiculo.objects.filter(ativo=True)
        clientes_qs = Cliente.objects.all()
        oportunidades_qs = Oportunidade.objects.all()
        
    # Metrics
    metrics = {
        # WMS
        "wms_total_recebimentos": entradas_qs.count(),
        "wms_recebimentos_pendentes": entradas_qs.filter(status__in=["pendente", "em_andamento"]).count(),
        "wms_total_produtos": produtos_qs.count(),
        
        # TMS
        "tms_total_romaneios": romaneios_qs.count(),
        "tms_romaneios_em_rota": romaneios_qs.filter(status__in=["em_rota", "com_ocorrencia"]).count(),
        "tms_total_motoristas": motoristas_qs.count(),
        "tms_total_veiculos": veiculos_qs.count(),
        
        # CRM
        "crm_total_clientes": clientes_qs.count(),
        "crm_total_oportunidades": oportunidades_qs.count(),
        "crm_oportunidades_ativas": oportunidades_qs.exclude(etapa__in=["fechado_ganho", "fechado_perdido"]).count(),
        "crm_valor_oportunidades": oportunidades_qs.exclude(etapa__in=["fechado_ganho", "fechado_perdido"]).aggregate(total=Sum("valor_estimado"))["total"] or 0,
    }
    
    # Recent Activities (last 5 of each)
    recent_entradas = entradas_qs.select_related("armazem", "responsavel").order_by("-chegada_em")[:5]
    recent_romaneios = romaneios_qs.select_related("veiculo", "motorista", "responsavel").order_by("-created_at")[:5]
    
    context = {
        "metrics": metrics,
        "recent_entradas": recent_entradas,
        "recent_romaneios": recent_romaneios,
        "empresa_nome": empresa.razao_social if empresa else "Super Administrador",
    }
    
    return render(request, "core/dashboard.html", context)
