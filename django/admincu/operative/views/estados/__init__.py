from datetime import datetime, date
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404 

from admincu.users.permissions import IsAccountOwner, IsComunidadMember, IsAdministrativoUser
from admincu.utils.generics import custom_viewsets

from admincu.operative.filters.operacion import OperacionFilter

from admincu.operative.models import (
	Naturaleza,
	Cuenta,
	Operacion,
	Titulo
)

from admincu.operative.serializers.estados import (
	EstadoCuentaModelSerializer,
	EstadoDeudasModelSerializer,
	# EstadoSaldosModelSerializer # En desuso
)

class Totalidad():

	def __init__(self, naturaleza, comunidad, *args, **kwargs):
		self.comunidad = comunidad
		self.naturaleza = Naturaleza.objects.get(nombre=naturaleza)
		self.naturalezas = [self.naturaleza.nombre]
		if self.naturaleza.nombre == "cliente":
			self.naturalezas.append("dominio")


	def estado_deuda(self, end_date=date.today()):	
		kwargs = {
			'cuenta__naturaleza__nombre__in': self.naturalezas,
			'vinculo__isnull': True,
			'documento__isnull': False,
			'documento__fecha_anulacion__isnull': True
		}
		if self.naturaleza.nombre in ['cliente', 'caja']:
			kwargs.update({'valor__gt': 0})
			if self.naturaleza.nombre == 'caja':
				kwargs.update({'cuenta__taxon__nombre': 'stockeable'})
		else:
			kwargs.update({'valor__lt': 0})
		deudas = Operacion.objects.filter(**kwargs)
		excluir = []
		for d in deudas:
			if d.saldo(fecha=fecha) <= 0:
				excluir.append(d.id)
		return deudas.exclude(id__in=excluir).order_by('-fecha', '-id')


	def estado_cuenta(self, end_date=date.today()):
		return Operacion.objects.filter(
				fecha__lte=fecha,
				documento__isnull=False,
			).order_by('fecha', 'id')

		
	def estado_saldos(self, end_date=date.today()):
		kwargs = {
			'cuenta__naturaleza__nombre__in': self.naturalezas,
			'vinculo__isnull': True,
			'documento__isnull': False,
			'documento__fecha_anulacion__isnull': True
		}
		if self.naturaleza.nombre in ['cliente']:
			kwargs.update({'valor__lt': 0})
		elif self.naturaleza.nombre in ['proveedor']:
			kwargs.update({'valor__gt': 0})

		if self.naturaleza.nombre == 'caja':
			kwargs.update({'cuenta__taxon__nombre': 'stockeable'})	
			
		saldos = Operacion.objects.filter(**kwargs)
		excluir = []
		for s in saldos:
			if s.saldo(fecha=fecha) <= 0:
				excluir.append(s.id)
		return saldos.exclude(id__in=excluir).order_by('-fecha', '-id')


class EstadosViewSet(custom_viewsets.CustomModelViewSet):
	"""
		Estado de cuenta para Clientes, Proveedores y Cajas.
		Deudas pendientes de cancelacion para Clientes y Proveedores.
	"""
	http_method_names = ['get']

	# naturalezas = ['cliente', 'proveedor', 'caja', 'ingreso']
	estados = {
		'cuenta': EstadoCuentaModelSerializer,
		'deudas': EstadoDeudasModelSerializer,
		'saldos': EstadoDeudasModelSerializer # Si existe la necesidad de tener separados los saldos de las deudas aunque utilicen el mismo serializer
	}

	filterset_class = OperacionFilter

	def get_queryset(self, **kwargs):
		fecha = datetime.strptime(self.request.GET['end_date'], "%Y-%m-%d").date() if 'end_date' in self.request.GET.keys() else date.today()
		obj = self.get_object()
		if self.kwargs['tipo'] == "deudas":
			datos = obj.estado_deuda(fecha=fecha)
		elif self.kwargs['tipo'] == "cuenta":
			datos = obj.estado_cuenta(fecha=fecha)
		elif self.kwargs['tipo'] == "saldos":
			datos = obj.estado_saldos(fecha=fecha)

		self.filter = self.filterset_class(self.request.GET, queryset=datos)
		return self.filter.qs

	def get_permissions(self):
		'''Manejo de permisos'''
		permissions = [IsAuthenticated, IsComunidadMember]
		if self.request.user.groups.all()[0].name == "socio":
			permissions.append(IsAccountOwner)
		else:
			permissions.append(IsAdministrativoUser)
		return [p() for p in permissions]


	def get_object(self):
		if self.kwargs["pk"].isdigit():
			if 'titulo' in self.request.GET.keys():
				obj = get_object_or_404(
						Titulo.objects.filter(comunidad=self.comunidad), 
						pk=self.kwargs["pk"]
					)
			else:
				obj = get_object_or_404(
						Cuenta.objects.filter(comunidad=self.comunidad), 
						pk=self.kwargs["pk"]
					)
		else:
			obj = Totalidad(naturaleza=self.kwargs["pk"], comunidad=self.comunidad)
		self.check_object_permissions(self.request, obj)
		return obj
		


	def get_serializer_class(self):
		'''Define el serializer segun parametro de url.'''
		try:
			return self.estados[self.kwargs['tipo']]
		except:
			raise Http404


	def retrieve(self, request, pk=None, **kwargs):
		queryset = self.get_queryset()
		obj = self.get_object()
		filtro = self.filter.data 
		end_date = filtro['end_date'] if 'end_date' in filtro.keys() else date.today()
		end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
		context = {
			'comunidad': self.comunidad,
			'cuenta': obj,
			'causante': "estado",
			'end_date': end_date,
			'sin_destinatario': False,
			'condonacion': filtro['condonacion'] if 'condonacion' in filtro.keys() else None
		}
		operaciones = self.get_serializer_class()(queryset, context=context, many=True)
		return Response(reversed(operaciones.data))