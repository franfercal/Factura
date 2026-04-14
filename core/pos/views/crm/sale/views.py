import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView

from core.pos.forms import *
from core.pos import printer
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin


class SaleListView(PermissionMixin, FormView):
    template_name = 'crm/sale/admin/list.html'
    form_class = ReportForm
    permission_required = 'view_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                queryset = Sale.objects.filter()
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset:
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in SaleDetail.objects.filter(sale_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('sale_admin_create')
        context['title'] = 'Listado de Ventas'
        return context


class SaleCreateView(PermissionMixin, CreateView):
    model = Sale
    template_name = 'crm/sale/admin/create.html'
    form_class = SaleForm
    success_url = reverse_lazy('sale_admin_list')
    permission_required = 'add_sale'

    def get_form(self, form_class=None):
        form = SaleForm()
        client = Client.objects.filter(user__dni='9999999999')
        if client.exists():
            client = client[0]
            form.fields['client'].queryset = Client.objects.filter(id=client.id)
            form.initial = {'client': client}
        return form

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    iva = float(Company.objects.first().iva) / 100
                    sale = Sale()
                    sale.employee_id = request.user.id
                    sale.client_id = int(request.POST['client'])
                    sale.payment_method = request.POST['payment_method']
                    sale.ticket_type = request.POST['ticket_type']
                    sale.iva = iva
                    sale.dscto = float(request.POST['dscto']) / 100
                    sale.save()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        detail = SaleDetail()
                        detail.sale_id = sale.id
                        detail.product_id = product.id
                        detail.price = float(i['price_current'])
                        detail.cant = int(i['cant'])
                        detail.iva = iva
                        detail.price_with_vat = detail.price + (detail.price * detail.iva)
                        detail.subtotal = detail.price * detail.cant
                        detail.total_iva = detail.subtotal * detail.iva
                        detail.dscto = float(i['dscto']) / 100
                        detail.total_dscto = detail.subtotal * detail.dscto
                        detail.total = detail.subtotal + detail.total_iva - detail.total_dscto
                        detail.save()
                        detail.product.stock -= detail.cant
                        detail.product.save()
                    sale.calculate_invoice()
                    if sale.payment_method == PAYMENT_METHOD[1][0]:
                        sale.end_credit = request.POST['end_credit']
                        sale.cash = 0.00
                        sale.change = 0.00
                        sale.save()
                        ctas_collect = CtasCollect()
                        ctas_collect.sale_id = sale.id
                        ctas_collect.date_joined = sale.date_joined
                        ctas_collect.end_date = sale.end_credit
                        ctas_collect.debt = sale.total
                        ctas_collect.saldo = sale.total
                        ctas_collect.save()
                    else:
                        sale.cash = float(request.POST['cash'])
                        sale.change = float(request.POST['change'])
                        sale.save()
                    sale.voucher_number = sale.generate_voucher_number()
                    sale.save()
                    print_url = reverse_lazy('sale_admin_print_invoice', kwargs={'pk': sale.id})
                    data = {'print_url': str(print_url)}
            elif action == 'search_products':
                ids = json.loads(request.POST['ids'])
                data = []
                term = request.POST['term']
                queryset = Product.objects.filter(Q(stock__gt=0) | Q(inventoried=False)).exclude(id__in=ids).order_by('name')
                if len(term):
                    queryset = queryset.filter(Q(name__icontains=term) | Q(code__icontains=term))
                    queryset = queryset[:10]
                for i in queryset:
                    item = i.toJSON()
                    item['pvp'] = float(i.pvp)
                    item['value'] = i.get_full_name()
                    item['dscto'] = '0.00'
                    item['total_dscto'] = '0.00'
                    data.append(item)
            elif action == 'search_client':
                data = []
                term = request.POST['term']
                for i in Client.objects.filter(Q(user__names__icontains=term) | Q(user__dni__icontains=term)).order_by('user__names')[0:10]:
                    item = i.toJSON()
                    item['text'] = i.get_full_name()
                    data.append(item)
            elif action == 'validate_client':
                data = {'valid': True}
                pattern = request.POST['pattern']
                parameter = request.POST['parameter'].strip()
                queryset = Client.objects.all()
                if pattern == 'dni':
                    data['valid'] = not queryset.filter(user__dni=parameter).exists()
                elif pattern == 'mobile':
                    data['valid'] = not queryset.filter(mobile=parameter).exists()
                elif pattern == 'email':
                    data['valid'] = not queryset.filter(user__email=parameter).exists()
            elif action == 'create_client':
                with transaction.atomic():
                    form1 = ClientUserForm(self.request.POST, self.request.FILES)
                    form2 = ClientForm(request.POST)
                    if form1.is_valid() and form2.is_valid():
                        user = form1.save(commit=False)
                        user.username = form1.cleaned_data.get('dni')
                        user.set_password(user.dni)
                        user.save()
                        user.groups.add(Group.objects.get(pk=settings.GROUPS.get('client')))
                        form_client = form2.save(commit=False)
                        form_client.user = user
                        form_client.save()
                        data = Client.objects.get(pk=form_client.id).toJSON()
                    else:
                        if not form1.is_valid():
                            data['error'] = form1.errors
                        elif not form2.is_valid():
                            data['error'] = form2.errors
            elif action == 'create_proforma':
                context = {'sale': json.loads(request.POST['items']), 'company': Company.objects.first(), 'employee': request.user, 'date_joined': datetime.now().date()}
                pdf_file = printer.create_pdf(context=context, template_name='crm/sale/format/proforma.html')
                return HttpResponse(pdf_file, content_type='application/pdf')
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['frmClient'] = ClientForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta'
        context['action'] = 'add'
        context['frmUser'] = ClientUserForm()
        return context


class SaleDeleteView(PermissionMixin, DeleteView):
    model = Sale
    template_name = 'crm/sale/admin/delete.html'
    success_url = reverse_lazy('sale_admin_list')
    permission_required = 'delete_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notificación de eliminación'
        context['list_url'] = self.success_url
        return context


class SalePrintInvoiceView(LoginRequiredMixin, View):
    success_url = reverse_lazy('sale_admin_list')

    def get_success_url(self):
        if self.request.user.is_client():
            return reverse_lazy('sale_client_list')
        return self.success_url

    def get_object(self):
        queryset = Sale.objects.filter(id=self.kwargs['pk'])
        if queryset.exists():
            return queryset[0]
        return None

    def get(self, request, *args, **kwargs):
        try:
            sale = self.get_object()
            if sale is not None:
                context = {'sale': sale, 'company': Company.objects.first(), 'height': 450 + sale.saledetail_set.all().count() * 10}
                if sale.ticket_type == TICKET_TYPE[0][0]:
                    pdf_file = printer.create_pdf(context=context, template_name='crm/sale/format/ticket.html')
                else:
                    pdf_file = printer.create_pdf(context=context, template_name='crm/sale/format/invoice.html')
                return HttpResponse(pdf_file, content_type='application/pdf')
        except:
            pass
        return HttpResponseRedirect(self.get_success_url())


class SaleClientListView(PermissionMixin, FormView):
    template_name = 'crm/sale/client/list.html'
    form_class = ReportForm
    permission_required = 'view_sale_client'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                queryset = Sale.objects.filter(client__user_id=request.user.id)
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset:
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in SaleDetail.objects.filter(sale_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Ventas'
        return context
