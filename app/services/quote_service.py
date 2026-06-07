from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud import quote_request, quote_response, quote_item
from app.models.quote_request import QuoteRequest, EstadoQuoteRequest
from app.models.quote_response import QuoteResponse, EstadoQuoteResponse
from app.models.quote_item import QuoteItem
from app.models.rol_usuario import RolUsuario
from app.models.persona import Persona
from app.models.usuario import Usuario
from app.models.solicitud_diagnostico import SolicitudDiagnostico, EstadoSolicitudDiagnostico
from app.models.diagnostico import Diagnostico
from app.models.solicitud_servicio import SolicitudServicio, EstadoSolicitudServicio, SugeridoPorTipo
from app.models.servicio import Servicio, EstadoServicio
from app.models.taller import Taller, EstadoTaller
from app.schemas.quote import (
    QuoteRequestCreate, QuoteRequestResponse, QuoteResponseCreate,
    QuoteAcceptRequest, TallerQuoteRequestResponse
)
from datetime import datetime, timedelta
from app.services.notification_service import NotificationService
from geoalchemy2 import functions as geofunc


class QuoteService:
    async def create_quote_request(
        self,
        db: AsyncSession,
        id_cliente: int,
        req: QuoteRequestCreate,
        foto_urls: Optional[List[str]] = None
    ) -> QuoteRequest:
        """Crea una solicitud de cotización y envía a los talleres seleccionados"""
        # Verificar que el vehículo pertenece al cliente
        from app.crud.crud_vehiculo import vehiculo
        vehicle = await vehiculo.get(db, req.id_vehiculo)
        if not vehicle or vehicle.id_persona != id_cliente:
            raise ValueError("El vehículo no pertenece al cliente")
        
        # Crear la solicitud de cotización
        ubicacion = None
        if req.ubicacion_lat is not None and req.ubicacion_lon is not None:
            ubicacion = f"{req.ubicacion_lat},{req.ubicacion_lon}"
        
        # Calcular fecha de expiración (1 hora)
        fecha_expiracion = datetime.utcnow() + timedelta(hours=1)
        
        quote_req = QuoteRequest(
            ubicacion=ubicacion,
            comentario=req.comentario,
            estado=EstadoQuoteRequest.pendiente,
            fecha_expiracion=fecha_expiracion,
            id_vehiculo=req.id_vehiculo,
            id_servicio=req.id_servicio,
            id_cliente=id_cliente,
            fotos=foto_urls
        )
        
        db.add(quote_req)
        await db.flush()
        
        # Crear respuestas pendientes para cada taller seleccionado
        for id_taller in req.ids_talleres:
            # Crear respuesta pendiente
            quote_resp = QuoteResponse(
                id_quote_request=quote_req.id,
                id_taller=id_taller,
                estado=EstadoQuoteResponse.pendiente
            )
            db.add(quote_resp)
        
        await db.commit()
        await db.refresh(quote_req, ["servicio"])
        
        # Enviar notificaciones a los talleres
        await _notificar_talleres_nueva_cotizacion(db, quote_req, req.ids_talleres)
        
        return quote_req
    
    async def get_client_quotes(
        self,
        db: AsyncSession,
        id_cliente: int,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[EstadoQuoteRequest] = None
    ) -> Tuple[List[QuoteRequest], int]:
        """Obtiene las solicitudes de cotización de un cliente"""
        return await quote_request.get_by_cliente(db, id_cliente, skip, limit, estado)
    
    async def get_quote_request_detail(
        self,
        db: AsyncSession,
        request_id: int,
        id_cliente: int
    ) -> Optional[QuoteRequest]:
        """Obtiene el detalle de una solicitud de cotización"""
        quote_req = await quote_request.get(db, request_id)
        if not quote_req or quote_req.id_cliente != id_cliente:
            return None
        return quote_req
    
    async def accept_quote(
        self,
        db: AsyncSession,
        request_id: int,
        req: QuoteAcceptRequest,
        id_cliente: int
    ) -> Optional[QuoteRequest]:
        """Acepta una cotización específica y rechaza las demás"""
        # Verificar que la solicitud pertenece al cliente
        quote_req = await quote_request.get(db, request_id)
        if not quote_req or quote_req.id_cliente != id_cliente:
            raise ValueError("La solicitud no pertenece al cliente")
        
        # Verificar que la respuesta pertenece a esta solicitud
        quote_resp = await quote_response.get(db, req.id_quote_response)
        if not quote_resp or quote_resp.id_quote_request != request_id:
            raise ValueError("La respuesta no pertenece a esta solicitud")
        
        # Verificar que la solicitud esté en estado con_respuesta
        if quote_req.estado != EstadoQuoteRequest.con_respuesta:
            raise ValueError("La solicitud no está en estado para aceptar cotizaciones")
        
        # Actualizar estado de la solicitud a aceptada
        await quote_request.update_estado(db, request_id, EstadoQuoteRequest.aceptada)
        
        # Actualizar estado de la respuesta aceptada
        await quote_response.update_estado(db, req.id_quote_response, EstadoQuoteResponse.respondida)
        
        # Marcar las otras respuestas como rechazadas
        await quote_response.mark_others_as_rejected(db, req.id_quote_response, request_id)
        
        await db.commit()
        await db.refresh(quote_req)
        
        # Crear diagnóstico, solicitud de servicio y servicio automáticamente
        await self._crear_servicio_desde_cotizacion(db, quote_req, quote_resp)
        
        # Enviar notificaciones a los talleres
        await _notificar_talleres_cotizacion_aceptada(db, quote_req, req.id_quote_response)
        
        return quote_req
    
    async def _crear_servicio_desde_cotizacion(
        self,
        db: AsyncSession,
        quote_req: QuoteRequest,
        quote_resp: QuoteResponse
    ) -> None:
        """Crea automáticamente un diagnóstico, solicitud de servicio y servicio a partir de una cotización aceptada"""
        try:
            # Convertir ubicación al formato correcto
            from geoalchemy2.shape import from_shape
            from shapely.geometry import Point
            
            ubicacion_geog = None
            if quote_req.ubicacion:
                try:
                    lat, lon = map(float, quote_req.ubicacion.split(','))
                    point = Point(lon, lat)
                    ubicacion_geog = from_shape(point, srid=4326)
                except Exception:
                    print(f"[ERROR] Error convirtiendo ubicación: {quote_req.ubicacion}")
            
            # 1. Crear SolicitudDiagnostico
            solicitud_diagnostico = SolicitudDiagnostico(
                descripcion="Cotización aceptada por cliente",
                estado=EstadoSolicitudDiagnostico.diagnosticada,
                ubicacion=ubicacion_geog,
                id_persona=quote_req.id_cliente,
                id_vehiculo=quote_req.id_vehiculo
            )
            db.add(solicitud_diagnostico)
            await db.flush()
            
            # 2. Crear Diagnóstico
            diagnostico = Diagnostico(
                descripcion="Servicio solicitado por cliente",
                nivel_confianza=1.0,  # 100% de confianza ya que fue aceptado manualmente
                id_solicitud_diagnostico=solicitud_diagnostico.id
            )
            db.add(diagnostico)
            await db.flush()
            
            # 3. Crear SolicitudServicio (estado pendiente para que el taller la acepte)
            solicitud_servicio = SolicitudServicio(
                ubicacion=ubicacion_geog,
                comentario=quote_req.comentario,
                estado=EstadoSolicitudServicio.pendiente,  # Pendiente para que el taller la acepte
                costo_estimado=quote_resp.total,
                sugerido_por=SugeridoPorTipo.conductor,
                id_taller=quote_resp.id_taller,
                id_diagnostico=diagnostico.id
            )
            db.add(solicitud_servicio)
            
            await db.commit()
            
            print(f"[DEBUG] Solicitud de servicio creada exitosamente: ID {solicitud_servicio.id}")
            
        except Exception as e:
            print(f"[ERROR] Error creando servicio desde cotización: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
    
    async def get_taller_pending_quotes(
        self,
        db: AsyncSession,
        id_taller: int,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[QuoteRequest], int]:
        """Obtiene las solicitudes de cotización pendientes para un taller"""
        return await quote_request.get_pending_for_taller(db, id_taller, skip, limit)
    
    async def get_taller_quote_detail(
        self,
        db: AsyncSession,
        request_id: int,
        id_taller: int
    ) -> Optional[QuoteRequest]:
        """Obtiene el detalle de una solicitud de cotización para un taller"""
        quote_req = await quote_request.get(db, request_id)
        if not quote_req:
            return None
        
        # Verificar que el taller tiene una respuesta para esta solicitud
        quote_resp = await quote_response.get_by_taller_and_request(db, id_taller, request_id)
        if not quote_resp:
            return None
        
        return quote_req
    
    async def respond_quote(
        self,
        db: AsyncSession,
        request_id: int,
        req: QuoteResponseCreate,
        id_taller: int
    ) -> Optional[QuoteResponse]:
        """El taller responde a una solicitud de cotización"""
        # Verificar que existe la solicitud
        quote_req = await quote_request.get(db, request_id)
        if not quote_req:
            raise ValueError("La solicitud no existe")
        
        # Verificar que el taller tiene una respuesta pendiente para esta solicitud
        quote_resp = await quote_response.get_by_taller_and_request(db, id_taller, request_id)
        if not quote_resp:
            raise ValueError("El taller no tiene una respuesta pendiente para esta solicitud")
        
        # Verificar que la respuesta esté pendiente
        if quote_resp.estado != EstadoQuoteResponse.pendiente:
            raise ValueError("El taller ya respondió a esta solicitud")
        
        # Verificar que la solicitud no esté expirada
        if quote_req.estado == EstadoQuoteRequest.expirada:
            raise ValueError("La solicitud está expirada")
        
        # Convertir items a dict
        items_data = [{"titulo": item.titulo, "precio": float(item.precio)} for item in req.items]
        
        # Crear la respuesta con items
        response = await quote_response.create_with_items(
            db, request_id, id_taller, items_data
        )
        
        await db.commit()
        await db.refresh(response)
        
        # Enviar notificación al cliente
        await _notificar_cliente_respuesta_cotizacion(db, quote_req.id, response)
        
        return response
    
    async def mark_expired_quotes(self, db: AsyncSession) -> List[QuoteRequest]:
        """Marca como expiradas las solicitudes que pasaron el tiempo límite"""
        return await quote_request.mark_expired(db)
    
    def format_ubicacion(self, ubicacion) -> Optional[str]:
        """Formatea la ubicación geográfica a string lat,lon"""
        if ubicacion is None:
            return None
        # Si ya es un string, devolverlo directamente
        if isinstance(ubicacion, str):
            return ubicacion
        return str(ubicacion)


# ============================================================================
# FUNCIONES AUXILIARES PARA NOTIFICACIONES
# ============================================================================

async def _notificar_talleres_nueva_cotizacion(
    db: AsyncSession,
    quote_req: QuoteRequest,
    ids_talleres: List[int]
) -> None:
    """Envía notificaciones a los talleres sobre una nueva solicitud de cotización"""
    try:
        notification_service = NotificationService()
        
        print(f"[DEBUG] Notificando a talleres: {ids_talleres}")
        
        # Obtener usuarios de los talleres seleccionados
        for id_taller in ids_talleres:
            # Verificar si el taller está activo
            result_taller = await db.execute(
                select(Taller).where(Taller.id == id_taller)
            )
            taller = result_taller.scalar_one_or_none()
            
            if not taller or taller.estado != EstadoTaller.activo:
                print(f"[DEBUG] Taller {id_taller} no existe o no está activo, omitiendo notificación")
                continue
            
            result = await db.execute(
                select(RolUsuario, Usuario, Persona).join(
                    Usuario, RolUsuario.id_usuario == Usuario.id
                ).join(
                    Persona, Usuario.id_persona == Persona.id
                ).where(RolUsuario.id_taller == id_taller)
            )
            
            roles = result.all()
            print(f"[DEBUG] Taller {id_taller}: {len(roles)} usuarios encontrados")
            
            for rol, usuario, persona in roles:
                # Obtener tokens FCM del usuario (a través de su persona)
                from app.crud.crud_dispositivo_usuario import dispositivo_usuario
                dispositivos = await dispositivo_usuario.get_by_persona(db, persona.id)
                tokens = [d.token_fcm for d in dispositivos if d.token_fcm and d.activo]
                
                print(f"[DEBUG] Usuario {persona.nombre} ({persona.id}): {len(tokens)} tokens activos")
                
                if tokens:
                    titulo = "Nueva Solicitud de Cotización"
                    mensaje = f"Un cliente ha solicitado una cotización para {quote_req.servicio.nombre if quote_req.servicio else 'un servicio'}"
                    
                    datos_extra = {
                        "tipo": "nueva_cotizacion",
                        "quote_request_id": str(quote_req.id),
                        "accion": "abrir_cotizaciones"
                    }
                    
                    print(f"[DEBUG] Enviando notificación a {len(tokens)} tokens")
                    await notification_service.enviar_notificacion_push(
                        tokens, titulo, mensaje, datos_extra
                    )
                    print(f"[DEBUG] Notificación enviada exitosamente")
                else:
                    print(f"[DEBUG] No hay tokens FCM activos para el usuario {persona.nombre}")
                    
    except Exception as e:
        print(f"[ERROR] Error notificando talleres: {e}")
        import traceback
        traceback.print_exc()


async def _notificar_cliente_respuesta_cotizacion(
    db: AsyncSession,
    quote_request_id: int,
    quote_resp: QuoteResponse
) -> None:
    """Envía notificación al cliente sobre una nueva respuesta de cotización"""
    try:
        notification_service = NotificationService()
        
        # Obtener el cliente
        result = await db.execute(
            select(QuoteRequest, Persona).join(
                Persona, QuoteRequest.id_cliente == Persona.id
            ).where(QuoteRequest.id == quote_request_id)
        )
        
        row = result.first()
        if not row:
            return
        
        quote_req, persona = row
        
        # Obtener tokens FCM del cliente
        from app.crud.crud_dispositivo_usuario import dispositivo_usuario
        dispositivos = await dispositivo_usuario.get_by_persona(db, persona.id)
        tokens = [d.token_fcm for d in dispositivos if d.token_fcm and d.activo]
        
        if tokens:
            titulo = "¡Nueva Cotización Recibida!"
            mensaje = f"Un taller ha respondido a tu solicitud de cotización"
            
            datos_extra = {
                "tipo": "respuesta_cotizacion",
                "quote_request_id": str(quote_request_id),
                "accion": "abrir_cotizacion_detalle"
            }
            
            await notification_service.enviar_notificacion_push(
                tokens, titulo, mensaje, datos_extra
            )
            
    except Exception as e:
        print(f"Error notificando cliente: {e}")


async def _notificar_talleres_cotizacion_aceptada(
    db: AsyncSession,
    quote_req: QuoteRequest,
    accepted_response_id: int
) -> None:
    """Envía notificaciones a los talleres sobre la aceptación/rechazo de cotización"""
    try:
        notification_service = NotificationService()
        
        # Obtener todas las respuestas
        respuestas = await quote_response.get_by_quote_request(db, quote_req.id)
        
        for resp in respuestas:
            # Verificar si el taller está activo
            result_taller = await db.execute(
                select(Taller).where(Taller.id == resp.id_taller)
            )
            taller = result_taller.scalar_one_or_none()
            
            if not taller or taller.estado != EstadoTaller.activo:
                print(f"[DEBUG] Taller {resp.id_taller} no existe o no está activo, omitiendo notificación")
                continue
            
            # Obtener usuarios del taller
            result = await db.execute(
                select(RolUsuario, Usuario, Persona).join(
                    Usuario, RolUsuario.id_usuario == Usuario.id
                ).join(
                    Persona, Usuario.id_persona == Persona.id
                ).where(RolUsuario.id_taller == resp.id_taller)
            )
            
            roles = result.all()
            
            for rol, usuario, persona in roles:
                # Obtener tokens FCM del usuario (a través de su persona)
                from app.crud.crud_dispositivo_usuario import dispositivo_usuario
                dispositivos = await dispositivo_usuario.get_by_persona(db, persona.id)
                tokens = [d.token_fcm for d in dispositivos if d.token_fcm and d.activo]
                
                if tokens:
                    if resp.id == accepted_response_id:
                        # Taller aceptado
                        titulo = "¡Cotización Aceptada!"
                        mensaje = f"El cliente ha aceptado tu cotización"
                        datos_extra = {
                            "tipo": "cotizacion_aceptada",
                            "quote_request_id": str(quote_req.id),
                            "accion": "abrir_cotizaciones"
                        }
                    else:
                        # Taller rechazado
                        titulo = "Cotización Rechazada"
                        mensaje = f"El cliente ha aceptado otra cotización"
                        datos_extra = {
                            "tipo": "cotizacion_rechazada",
                            "quote_request_id": str(quote_req.id),
                            "accion": "abrir_cotizaciones"
                        }
                    
                    await notification_service.enviar_notificacion_push(
                        tokens, titulo, mensaje, datos_extra
                    )
                    
    except Exception as e:
        print(f"Error notificando talleres aceptación: {e}")


quote_service = QuoteService()
