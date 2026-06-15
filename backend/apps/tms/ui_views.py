from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from .models import Romaneio, Motorista, Veiculo, ItemRomaneio, Ocorrencia, POD

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
            data_saida_prevista=previsao_saida or None,
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
        cpf = request.POST.get("cpf")
        categoria_cnh = request.POST.get("categoria_cnh", "B")
        validade_cnh = request.POST.get("validade_cnh")
        telefone = request.POST.get("telefone")
        
        Motorista.objects.create(
            empresa=request.user.empresa,
            nome_completo=nome,
            cpf=cpf,
            cnh=cnh,
            categoria_cnh=categoria_cnh,
            validade_cnh=validade_cnh or None,
            telefone=telefone,
            ativo=True
        )
        
        motoristas = Motorista.objects.filter(
            empresa=request.user.empresa
        ).order_by("nome_completo")
        
        return render(request, "tms/partials/tabela_motoristas.html", {"motoristas": motoristas})


@login_required(login_url="/admin/login/")
def romaneio_detalhe(request, pk):
    # Tenant check
    empresa = request.user.empresa
    if empresa:
        romaneio = get_object_or_404(Romaneio, id=pk, empresa=empresa)
    else:
        romaneio = get_object_or_404(Romaneio, id=pk)
        
    itens = romaneio.itens.select_related("cliente_crm", "saida_wms").order_by("ordem_entrega")
    ocorrencias = romaneio.ocorrencias.select_related("item", "registrado_por").order_by("-created_at")
    
    context = {
        "romaneio": romaneio,
        "itens": itens,
        "ocorrencias": ocorrencias,
    }
    return render(request, "tms/romaneio_detalhe.html", context)


@login_required(login_url="/admin/login/")
def romaneio_iniciar(request, pk):
    if request.method == "POST":
        empresa = request.user.empresa
        if empresa:
            romaneio = get_object_or_404(Romaneio, id=pk, empresa=empresa)
        else:
            romaneio = get_object_or_404(Romaneio, id=pk)
            
        try:
            romaneio.iniciar_rota(request.user)
        except ValueError as e:
            # Em caso de erro, por simplificação passaremos no response (ou ignorado)
            pass
            
        # Se for requisição HTMX, podemos redirecionar via cabeçalho
        if request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("tms_ui:romaneio_detalhe", kwargs={"pk": pk})
            return response
            
        return redirect("tms_ui:romaneio_detalhe", pk=pk)


@login_required(login_url="/admin/login/")
def romaneio_concluir_ui(request, pk):
    if request.method == "POST":
        empresa = request.user.empresa
        if empresa:
            romaneio = get_object_or_404(Romaneio, id=pk, empresa=empresa)
        else:
            romaneio = get_object_or_404(Romaneio, id=pk)
            
        try:
            romaneio.concluir(request.user)
        except ValueError as e:
            pass
            
        if request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("tms_ui:romaneio_detalhe", kwargs={"pk": pk})
            return response
            
        return redirect("tms_ui:romaneio_detalhe", pk=pk)


@login_required(login_url="/admin/login/")
def item_confirmar_entrega(request, item_id):
    empresa = request.user.empresa
    if empresa:
        item = get_object_or_404(ItemRomaneio, id=item_id, romaneio__empresa=empresa)
    else:
        item = get_object_or_404(ItemRomaneio, id=item_id)
        
    if request.method == "GET":
        # Retorna o formulário modal
        return render(request, "tms/partials/modal_pod.html", {"item": item})
        
    if request.method == "POST":
        assinado_por = request.POST.get("assinado_por", "").strip()
        observacao = request.POST.get("observacao", "").strip()
        
        # Geolocalização
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        
        lat_float = float(latitude) if latitude else None
        lng_float = float(longitude) if longitude else None
        
        # Criação do POD automaticamente define status_entrega do item como 'entregue'
        POD.objects.create(
            item=item,
            assinado_por=assinado_por or "Não informado",
            observacao=observacao,
            latitude=lat_float,
            longitude=lng_float
        )
        
        # Se for requisição HTMX, retorna a lista atualizada de itens e fecha o modal
        if request.headers.get("HX-Request"):
            response = render(request, "tms/partials/detalhes_itens.html", {
                "romaneio": item.romaneio,
                "itens": item.romaneio.itens.select_related("cliente_crm", "saida_wms").order_by("ordem_entrega")
            })
            # Trigger para o Alpine fechar o modal
            response["HX-Trigger"] = "close-modal"
            return response
            
        return redirect("tms_ui:romaneio_detalhe", pk=item.romaneio.id)


@login_required(login_url="/admin/login/")
def ocorrencia_registrar(request, romaneio_id):
    empresa = request.user.empresa
    if empresa:
        romaneio = get_object_or_404(Romaneio, id=romaneio_id, empresa=empresa)
    else:
        romaneio = get_object_or_404(Romaneio, id=romaneio_id)
        
    if request.method == "GET":
        itens = romaneio.itens.all()
        return render(request, "tms/partials/modal_ocorrencia.html", {
            "romaneio": romaneio,
            "itens": itens
        })
        
    if request.method == "POST":
        tipo = request.POST.get("tipo")
        descricao = request.POST.get("descricao")
        item_id = request.POST.get("item_id")
        
        item = None
        if item_id:
            item = romaneio.itens.filter(id=item_id).first()
            
        Ocorrencia.objects.create(
            romaneio=romaneio,
            item=item,
            tipo=tipo,
            descricao=descricao,
            registrado_por=request.user
        )
        
        # Redireciona HTMX de volta ao detalhe (pois pode mudar status do romaneio para com_ocorrencia)
        if request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("tms_ui:romaneio_detalhe", kwargs={"pk": romaneio_id})
            return response
            
        return redirect("tms_ui:romaneio_detalhe", pk=romaneio_id)
