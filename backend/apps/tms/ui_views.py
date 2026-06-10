from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Romaneio, Motorista, Veiculo

@login_required(login_url="/admin/login/")
def romaneios_list(request):
    romaneios = Romaneio.objects.filter(
        empresa=request.user.empresa
    ).select_related("veiculo", "motorista", "responsavel").order_by("-created_at")
    
    veiculos = Veiculo.objects.filter(empresa=request.user.empresa, ativo=True)
    motoristas = Motorista.objects.filter(empresa=request.user.empresa, ativo=True)
    
    if request.headers.get("HX-Request"):
        q = request.GET.get("q", "")
        status = request.GET.get("status", "")
        
        if q:
            romaneios = romaneios.filter(numero__icontains=q)
        if status and status != "Todos":
            status_map = {
                "Aberto": "aberto",
                "Em Rota": "em_rota",
                "Concluído": "concluido",
                "Com Ocorrência": "com_ocorrencia",
                "Cancelado": "cancelado"
            }
            if status in status_map:
                romaneios = romaneios.filter(status=status_map[status])
                
        return render(request, "tms/partials/tabela_romaneios.html", {"romaneios": romaneios})

    context = {
        "romaneios": romaneios,
        "veiculos": veiculos,
        "motoristas": motoristas
    }
    return render(request, "tms/romaneios.html", context)


@login_required(login_url="/admin/login/")
def romaneio_criar(request):
    if request.method == "POST":
        numero = request.POST.get("numero")
        veiculo_id = request.POST.get("veiculo_id")
        motorista_id = request.POST.get("motorista_id")
        previsao_saida = request.POST.get("previsao_saida")
        
        veiculo = Veiculo.objects.filter(id=veiculo_id, empresa=request.user.empresa).first() if veiculo_id else None
        motorista = Motorista.objects.filter(id=motorista_id, empresa=request.user.empresa).first() if motorista_id else None
        
        Romaneio.objects.create(
            empresa=request.user.empresa,
            responsavel=request.user,
            numero=numero,
            veiculo=veiculo,
            motorista=motorista,
            previsao_saida=previsao_saida or None,
            status="aberto"
        )
        
        romaneios = Romaneio.objects.filter(
            empresa=request.user.empresa
        ).select_related("veiculo", "motorista", "responsavel").order_by("-created_at")
        
        return render(request, "tms/partials/tabela_romaneios.html", {"romaneios": romaneios})


@login_required(login_url="/admin/login/")
def motoristas_list(request):
    motoristas = Motorista.objects.filter(
        empresa=request.user.empresa
    ).order_by("nome_completo")
    
    if request.headers.get("HX-Request"):
        q = request.GET.get("q", "")
        if q:
            motoristas = motoristas.filter(nome_completo__icontains=q)
                
        return render(request, "tms/partials/tabela_motoristas.html", {"motoristas": motoristas})

    return render(request, "tms/motoristas.html", {"motoristas": motoristas})


@login_required(login_url="/admin/login/")
def motorista_criar(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        cnh = request.POST.get("cnh")
        telefone = request.POST.get("telefone")
        
        Motorista.objects.create(
            empresa=request.user.empresa,
            nome_completo=nome,
            cnh=cnh,
            telefone=telefone,
            ativo=True
        )
        
        motoristas = Motorista.objects.filter(
            empresa=request.user.empresa
        ).order_by("nome_completo")
        
        return render(request, "tms/partials/tabela_motoristas.html", {"motoristas": motoristas})
