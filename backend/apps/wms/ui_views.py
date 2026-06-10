from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import EntradaMercadoria

# Se quiser usar o login_required, o auth precisaria estar configurado.
# Como no momento é via JWT/API, talvez para a UI precisemos do SessionAuthentication.
# Por enquanto vou assumir que há um request.user (se logar no admin, funciona).
@login_required(login_url="/admin/login/")
def recebimentos_list(request):
    entradas = EntradaMercadoria.objects.filter(
        armazem__empresa=request.user.empresa
    ).select_related("armazem", "responsavel").order_by("-chegada_em")
    
    # Se for uma requisição HTMX, retornar apenas o fragmento da tabela
    if request.headers.get("HX-Request"):
        # Lógica de filtro simples
        q = request.GET.get("q", "")
        status = request.GET.get("status", "")
        
        if q:
            entradas = entradas.filter(numero_nf__icontains=q)
        if status and status != "Todos os status":
            # mapear "Pendente" para "pendente", etc
            status_map = {
                "Pendente": "pendente",
                "Em andamento": "andamento",
                "Concluído": "concluido",
                "Divergência": "divergencia"
            }
            if status in status_map:
                entradas = entradas.filter(status=status_map[status])
                
        return render(request, "wms/partials/tabela_recebimentos.html", {"entradas": entradas})

    # Requisição normal, renderiza a página completa
    return render(request, "wms/recebimentos.html", {"entradas": entradas})


from django.utils import timezone

@login_required(login_url="/admin/login/")
def recebimento_criar(request):
    if request.method == "POST":
        numero_nf = request.POST.get("numero_nf")
        fornecedor = request.POST.get("fornecedor")
        
        armazem = request.user.empresa.armazens.first()
        if not armazem:
            # Fallback or error
            pass
            
        EntradaMercadoria.objects.create(
            armazem=armazem,
            responsavel=request.user,
            numero_nf=numero_nf,
            fornecedor=fornecedor,
            chegada_em=timezone.now(),
            status="pendente"
        )
        
        # Recarregar as entradas e retornar o fragmento da tabela
        entradas = EntradaMercadoria.objects.filter(
            armazem__empresa=request.user.empresa
        ).select_related("armazem", "responsavel").order_by("-chegada_em")
        
        return render(request, "wms/partials/tabela_recebimentos.html", {"entradas": entradas})

