import math
from datetime import datetime

from django.db import models
from django.db.models import FloatField
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.forms import model_to_dict

from config import settings
from core.pos.choices import *
from core.user.models import User


class Company(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre')
    ruc = models.CharField(max_length=13, verbose_name='Ruc')
    address = models.CharField(max_length=200, verbose_name='Dirección')
    mobile = models.CharField(max_length=10, verbose_name='Teléfono celular')
    phone = models.CharField(max_length=9, verbose_name='Teléfono convencional')
    email = models.CharField(max_length=50, verbose_name='Email')
    website = models.CharField(max_length=250, verbose_name='Página web')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Descripción')
    image = models.ImageField(null=True, blank=True, upload_to='company/%Y/%m/%d', verbose_name='Logotipo de la empresa')
    iva = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='IVA')

    def __str__(self):
        return self.name

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_full_path_image(self):
        if self.image:
            return self.image.path
        return f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/empty.png'

    def get_iva(self):
        return float(self.iva)

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        default_permissions = ()
        permissions = (
            ('view_company', 'Can view Empresa'),
        )
        ordering = ['-id']


class Provider(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nombre')
    ruc = models.CharField(max_length=13, unique=True, verbose_name='Ruc')
    mobile = models.CharField(max_length=10, unique=True, verbose_name='Teléfono celular')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección')
    email = models.CharField(max_length=50, unique=True, verbose_name='Email')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.ruc})'

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['-id']


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['-id']


class Product(models.Model):
    name = models.CharField(max_length=150, verbose_name='Nombre')
    code = models.CharField(max_length=8, unique=True, verbose_name='Código')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Descripción')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Categoría')
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Compra')
    pvp = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Venta')
    image = models.ImageField(upload_to='product/%Y/%m/%d', null=True, blank=True, verbose_name='Imagen')
    inventoried = models.BooleanField(default=True, verbose_name='¿Es inventariado?')
    stock = models.IntegerField(default=0)
    with_tax = models.BooleanField(default=True, verbose_name='¿Se cobra impuesto?')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.code}) ({self.category.name})'

    def get_short_name(self):
        return f'{self.name} ({self.category.name})'

    def get_or_create_category(self, name):
        category = Category()
        search = Category.objects.filter(name=name)
        if search.exists():
            category = search[0]
        else:
            category.name = name
            category.save()
        return category

    def get_inventoried(self):
        if self.inventoried:
            return 'Inventariado'
        return 'No inventariado'

    def toJSON(self):
        item = model_to_dict(self)
        item['full_name'] = self.get_full_name()
        item['short_name'] = self.get_short_name()
        item['category'] = self.category.toJSON()
        item['price'] = float(self.price)
        item['price_promotion'] = float(self.get_price_promotion())
        item['price_current'] = float(self.get_price_current())
        item['pvp'] = float(self.pvp)
        item['image'] = self.get_image()
        return item

    def get_price_promotion(self):
        promotions = self.promotionsdetail_set.filter(promotion__state=True)
        if promotions.exists():
            return promotions[0].price_final
        return 0.00

    def get_price_current(self):
        price_promotion = self.get_price_promotion()
        if price_promotion > 0:
            return price_promotion
        return self.pvp

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_benefit(self):
        benefit = float(self.pvp) - float(self.price)
        return round(benefit, 2)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        default_permissions = ()
        permissions = (
            ('view_product', 'Can view Producto'),
            ('add_product', 'Can add Producto'),
            ('change_product', 'Can change Producto'),
            ('delete_product', 'Can delete Producto'),
            ('adjust_product_stock', 'Can adjust_product_stock Producto'),
        )
        ordering = ['-name']


class Purchase(models.Model):
    number = models.CharField(max_length=8, unique=True, verbose_name='Número de factura')
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, verbose_name='Proveedor')
    payment_method = models.CharField(choices=PAYMENT_METHOD, max_length=50, default=PAYMENT_METHOD[0][0], verbose_name='Método de pago')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha de plazo de credito')
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.provider.name

    def calculate_detail(self):
        for detail in self.purchasedetail_set.filter():
            detail.subtotal = detail.price * detail.cant
            detail.save()

    def calculate_invoice(self):
        self.subtotal = float(self.purchasedetail_set.all().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField())).get('result'))
        self.save()

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.purchasedetail_set.all():
                i.product.stock -= i.cant
                i.product.save()
                i.delete()
        except:
            pass
        super(Purchase, self).delete()

    def toJSON(self):
        item = model_to_dict(self)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['provider'] = self.provider.toJSON()
        item['payment_method'] = {'id': self.payment_method, 'name': self.get_payment_method_display()}
        item['subtotal'] = float(self.subtotal)
        return item

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        default_permissions = ()
        permissions = (
            ('view_purchase', 'Can view Compra'),
            ('add_purchase', 'Can add Compra'),
            ('delete_purchase', 'Can delete Compra'),
        )
        ordering = ['-id']


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    cant = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def toJSON(self):
        item = model_to_dict(self, exclude=['purchase'])
        item['product'] = self.product.toJSON()
        item['price'] = float(self.price)
        item['dscto'] = float(self.dscto)
        item['subtotal'] = float(self.subtotal)
        return item

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalle de Compras'
        default_permissions = ()
        ordering = ['-id']


class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=10, unique=True, verbose_name='Teléfono')
    birthdate = models.DateField(default=datetime.now, verbose_name='Fecha de nacimiento')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return self.user.get_full_name()

    def birthdate_format(self):
        return self.birthdate.strftime('%Y-%m-%d')

    def toJSON(self):
        item = model_to_dict(self)
        item['user'] = self.user.toJSON()
        item['birthdate'] = self.birthdate.strftime('%Y-%m-%d')
        return item

    def delete(self, using=None, keep_parents=False):
        super(Client, self).delete()
        try:
            self.user.delete()
        except:
            pass

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-id']


class Sale(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, verbose_name='Cliente')
    employee = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Empleado')
    voucher_number = models.CharField(max_length=9, verbose_name='Número de comprobante')
    payment_method = models.CharField(choices=PAYMENT_METHOD, max_length=50, default=PAYMENT_METHOD[0][0], verbose_name='Método de pago')
    ticket_type = models.CharField(choices=TICKET_TYPE, max_length=50, default=TICKET_TYPE[0][0], verbose_name='Tipo de Ticket')
    creation_date = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora de registro')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha limite de credito')
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal')
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Descuento')
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor del descuento')
    iva = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Iva')
    total_iva = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor de iva')
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total a pagar')
    cash = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Efectivo')
    change = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Cambio')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.client.user.names} / {self.voucher_number}'

    def generate_voucher_number(self):
        return f'{self.id:06d}'

    def toJSON(self):
        item = model_to_dict(self)
        item['client'] = self.client.toJSON()
        item['employee'] = self.employee.toJSON()
        item['payment_method'] = {'id': self.payment_method, 'name': self.get_payment_method_display()}
        item['ticket_type'] = {'id': self.ticket_type, 'name': self.get_ticket_type_display()}
        item['creation_date'] = self.creation_date.strftime('%Y-%m-%d %H:%M:%S')
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['subtotal'] = float(self.subtotal)
        item['dscto'] = float(self.dscto)
        item['total_dscto'] = float(self.total_dscto)
        item['iva'] = float(self.iva)
        item['total_iva'] = float(self.total_iva)
        item['total'] = float(self.total)
        item['cash'] = float(self.cash)
        item['change'] = float(self.change)
        return item

    def calculate_detail(self):
        for detail in self.saledetail_set.filter():
            detail.price = float(detail.price)
            detail.iva = float(self.iva)
            detail.price_with_vat = detail.price + (detail.price * detail.iva)
            detail.subtotal = detail.price * detail.cant
            detail.total_iva = detail.subtotal * detail.iva
            detail.total_dscto = detail.subtotal * float(detail.dscto)
            detail.total = detail.subtotal + detail.total_iva - detail.total_dscto
            detail.save()

    def calculate_invoice(self):
        self.subtotal = float(self.saledetail_set.all().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField())).get('result'))
        self.total_iva = float(self.saledetail_set.all().aggregate(result=Coalesce(Sum('total_iva'), 0.00, output_field=FloatField())).get('result'))
        self.total_dscto = self.subtotal * float(self.dscto)
        self.total = float(self.subtotal) - float(self.total_dscto) + float(self.total_iva)
        self.save()

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.saledetail_set.filter(product__inventoried=True):
                i.product.stock += i.cant
                i.product.save()
                i.delete()
        except:
            pass
        super(Sale, self).delete()

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        default_permissions = ()
        permissions = (
            ('view_sale', 'Can view Venta'),
            ('add_sale', 'Can add Venta'),
            ('delete_sale', 'Can delete Venta'),
            ('view_sale_client', 'Can view_sale_client Venta'),
        )
        ordering = ['-id']


class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    cant = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_with_vat = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_iva = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def toJSON(self):
        item = model_to_dict(self, exclude=['sale'])
        item['product'] = self.product.toJSON()
        item['price'] = float(self.price)
        item['price_with_vat'] = float(self.price_with_vat)
        item['subtotal'] = float(self.subtotal)
        item['iva'] = float(self.subtotal)
        item['total_iva'] = float(self.subtotal)
        item['dscto'] = float(self.dscto)
        item['total_dscto'] = float(self.total_dscto)
        item['total'] = float(self.total)
        return item

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalle de Ventas'
        default_permissions = ()
        ordering = ['-id']


class CtasCollect(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    saldo = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    state = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.sale.client.user.names} ({self.sale.client.user.dni}) / {self.date_joined.strftime('%Y-%m-%d')} / ${float(self.debt)}"

    def validate_debt(self):
        try:
            saldo = self.paymentsctacollect_set.aggregate(result=Coalesce(Sum('valor'), 0.00, output_field=FloatField())).get('result')
            self.saldo = float(self.debt) - float(saldo)
            self.state = self.saldo > 0.00
            self.save()
        except:
            pass

    def toJSON(self):
        item = model_to_dict(self)
        item['sale'] = self.sale.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['saldo'] = float(self.saldo)
        return item

    class Meta:
        verbose_name = 'Cuenta por cobrar'
        verbose_name_plural = 'Cuentas por cobrar'
        default_permissions = ()
        permissions = (
            ('view_ctas_collect', 'Can view Cuenta por cobrar'),
            ('add_ctas_collect', 'Can add Cuenta por cobrar'),
            ('delete_ctas_collect', 'Can delete Cuenta por cobrar'),
        )
        ordering = ['-id']


class PaymentsCtaCollect(models.Model):
    ctas_collect = models.ForeignKey(CtasCollect, on_delete=models.CASCADE, verbose_name='Cuenta por cobrar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')

    def __str__(self):
        return self.ctas_collect.id

    def toJSON(self):
        item = model_to_dict(self, exclude=['ctas_collect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = float(self.valor)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.description is None:
            self.description = 's/n'
        elif len(self.description) == 0:
            self.description = 's/n'
        super(PaymentsCtaCollect, self).save()

    class Meta:
        verbose_name = 'Pago Cuenta por cobrar'
        verbose_name_plural = 'Pagos Cuentas por cobrar'
        default_permissions = ()
        ordering = ['-id']


class DebtsPay(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    saldo = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    state = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.purchase.provider.name} ({self.purchase.number}) / {self.date_joined.strftime('%Y-%m-%d')} / ${float(self.debt)}"

    def validate_debt(self):
        try:
            saldo = self.paymentsdebtspay_set.aggregate(result=Coalesce(Sum('valor'), 0.00, output_field=FloatField())).get('result')
            self.saldo = float(self.debt) - float(saldo)
            self.state = self.saldo > 0.00
            self.save()
        except:
            pass

    def toJSON(self):
        item = model_to_dict(self)
        item['purchase'] = self.purchase.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['saldo'] = float(self.saldo)
        return item

    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_debts_pay', 'Can view Cuenta por pagar'),
            ('add_debts_pay', 'Can add Cuenta por pagar'),
            ('delete_debts_pay', 'Can delete Cuenta por pagar'),
        )
        ordering = ['-id']


class PaymentsDebtsPay(models.Model):
    debts_pay = models.ForeignKey(DebtsPay, on_delete=models.CASCADE, verbose_name='Cuenta por pagar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')

    def __str__(self):
        return self.debts_pay.id

    def toJSON(self):
        item = model_to_dict(self, exclude=['debts_pay'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = float(self.valor)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.description is None:
            self.description = 's/n'
        elif len(self.description) == 0:
            self.description = 's/n'
        super(PaymentsDebtsPay, self).save()

    class Meta:
        verbose_name = 'Det. Cuenta por pagar'
        verbose_name_plural = 'Det. Cuentas por pagar'
        default_permissions = ()
        ordering = ['-id']


class TypeExpense(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Tipo de Gasto'
        verbose_name_plural = 'Tipos de Gastos'
        default_permissions = ()
        permissions = (
            ('view_type_expense', 'Can view Tipo de Gasto'),
            ('add_type_expense', 'Can add Tipo de Gasto'),
            ('change_type_expense', 'Can change Tipo de Gasto'),
            ('delete_type_expense', 'Can delete Tipo de Gasto'),
        )
        ordering = ['id']


class Expenses(models.Model):
    type_expense = models.ForeignKey(TypeExpense, on_delete=models.PROTECT, verbose_name='Tipo de Gasto')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='Descripción')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de Registro')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')

    def __str__(self):
        return self.description

    def toJSON(self):
        item = model_to_dict(self)
        item['type_expense'] = self.type_expense.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = float(self.valor)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.description is None:
            self.description = 's/n'
        elif len(self.description) == 0:
            self.description = 's/n'
        super(Expenses, self).save()

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['id']


class Promotions(models.Model):
    start_date = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    state = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def toJSON(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-id']


class PromotionsDetail(models.Model):
    promotion = models.ForeignKey(Promotions, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price_current = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_final = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def get_dscto_real(self):
        total_dscto = float(self.price_current) * float(self.dscto)
        n = 2
        return math.floor(total_dscto * 10 ** n) / 10 ** n

    def toJSON(self):
        item = model_to_dict(self, exclude=['promotion'])
        item['product'] = self.product.toJSON()
        item['price_current'] = float(self.price_current)
        item['dscto'] = float(self.dscto)
        item['total_dscto'] = float(self.total_dscto)
        item['price_final'] = float(self.price_final)
        return item

    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        default_permissions = ()
        ordering = ['-id']


class Devolution(models.Model):
    sale_detail = models.ForeignKey(SaleDetail, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    cant = models.IntegerField(default=0)
    motive = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.motive

    def toJSON(self):
        item = model_to_dict(self)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['sale_detail'] = self.sale_detail.toJSON()
        item['motive'] = 'Sin detalles' if len(self.motive) == 0 else self.motive
        return item

    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        default_permissions = ()
        permissions = (
            ('view_devolution', 'Can view Devolución'),
            ('add_devolution', 'Can add Devolución'),
            ('delete_devolution', 'Can delete Devolución'),
        )
        ordering = ['-id']
