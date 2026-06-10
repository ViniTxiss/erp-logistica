from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Cliente, Oportunidade, EtapaOportunidade

@login_required(login_url="/admin/login/")
def clientes_list(request):
    clientes = Cliente.objects.filter(
        empresa=request.user.empresa
    ).order_by("razao_social")
    
    if request.headers.get("HX-Request"):
        q = request.GET.get("q", "")
        status = request.GET.get("status", "")
        
        if q:
            clientes = clientes.filter(razao_social__icontains=q)
        if status and status != "Todos":
            status_map = {
                "Lead": "lead",
                "Ativo": "ativo",
                "Inativo": "inativo",
                "Bloqueado": "bloqueado"
            }
            if status in status_map:
                clientes = clientes.filter(status=status_map[status])
                
        return render(request, "crm/partials/tabela_clientes.html", {"clientes": clientes})

    return render(request, "crm/clientes.html", {"clientes": clientes})


@login_required(login_url="/admin/login/")
def cliente_criar(request):
    if request.method == "POST":
        razao_social = request.POST.get("razao_social")
        cnpj = request.POST.get("cnpj")
        segmento = request.POST.get("segmento", "outro")
        email = request.POST.get("email", "")
        telefone = request.POST.get("telefone", "")
        
        Cliente.objects.create(
            empresa=request.user.empresa,
            razao_social=razao_social,
            cnpj=cnpj,
            segmento=segmento,
            email_principal=email,
            telefone=telefone,
            status="lead",
            responsavel=request.user
        )
        
        clientes = Cliente.objects.filter(
            empresa=request.user.empresa
        ).order_by("razao_social")
        
        return render(request, "crm/partials/tabela_clientes.html", {"clientes": clientes})


@login_required(login_url="/admin/login/")
def oportunidades_list(request):
    oportunidades = Oportunidade.objects.filter(
        cliente__empresa=request.user.empresa
    ).select_related("cliente")
    
    # Agrupando por etapa para o Kanban
    kanban_data = {
        "prospeccao": oportunidades.filter(etapa="prospeccao"),
        "qualificacao": oportunidades.filter(etapa="qualificacao"),
        "proposta": oportunidades.filter(etapa="proposta"),
        "negociacao": oportunidades.filter(etapa="negociacao"),
        "fechado_ganho": oportunidades.filter(etapa="fechado_ganho"),
        "fechado_perdido": oportunidades.filter(etapa="fechado_perdido"),
    }
    
    clientes_para_select = Cliente.objects.filter(empresa=request.user.empresa)
    
    if request.headers.get("HX-Request"):
        return render(request, "crm/partials/kanban_oportunidades.html", {"kanban_data": kanban_data})

    return render(request, "crm/oportunidades.html", {
        "kanban_data": kanban_data,
        "clientes": clientes_para_select
    })


@login_required(login_url="/admin/login/")
def oportunidade_criar(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        titulo = request.POST.get("titulo")
        servico = request.POST.get("servico", "frete")
        valor_estimado = request.POST.get("valor_estimado") or None
        
        cliente = Cliente.objects.filter(id=cliente_id, empresa=request.user.empresa).first()
        
        if cliente:
            Oportunidade.objects.create(
                cliente=cliente,
                titulo=titulo,
                servico=servico,
                valor_estimado=valor_estimado,
                etapa="prospeccao",
                responsavel=request.user
            )
        
        oportunidades = Oportunidade.objects.filter(
            cliente__empresa=request.user.empresa
        ).select_related("cliente")
        
        kanban_data = {
            "prospeccao": oportunidades.filter(etapa="prospeccao"),
            "qualificacao": oportunidades.filter(etapa="qualificacao"),
            "proposta": oportunidades.filter(etapa="proposta"),
            "negociacao": oportunidades.filter(etapa="negociacao"),
            "fechado_ganho": oportunidades.filter(etapa="fechado_ganho"),
            "fechado_perdido": oportunidades.filter(etapa="fechado_perdido"),
        }
        
        return render(request, "crm/partials/kanban_oportunidades.html", {"kanban_data": kanban_data})
