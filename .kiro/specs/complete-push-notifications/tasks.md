# Implementation Plan: Complete Push Notifications System

## Overview

This implementation plan covers the complete push notifications system across three components:
- **Backend (P2-backend)**: Enhance existing NotificationService with missing workshop notifications and token management
- **Mobile (P2-mobile)**: Integrate navigation handlers with actual routes
- **Web (P2-frontend)**: Implement full Firebase integration from scratch

The implementation follows the order: Backend → Mobile → Web, ensuring each layer is functional before moving to the next.

## Tasks

### 1. Backend: Database Schema Enhancements

- [ ] 1.1 Create database migration for DispositivoUsuario table enhancements
  - Add columns: `plataforma` (VARCHAR(20)), `activo` (BOOLEAN DEFAULT TRUE), `fecha_registro` (TIMESTAMP), `fecha_ultima_actividad` (TIMESTAMP)
  - Add UNIQUE constraint on `token_fcm` column
  - Create indexes on `token_fcm`, `id_persona`, and `activo` columns
  - Write Alembic migration script in `P2-backend/alembic/versions/`
  - _Requirements: 22.1, 22.2, 23.1, 23.2_

- [ ] 1.2 Run database migration
  - Execute migration using `alembic upgrade head`
  - Verify schema changes in database
  - _Requirements: 22.1, 23.1_

### 2. Backend: NotificationService Enhancements

- [x] 2.1 Implement workshop notification methods in NotificationService
  - Add `notificar_nueva_solicitud_taller()` method for new service requests
  - Add `notificar_solicitud_cancelada_taller()` method for cancelled requests
  - Add `notificar_diagnostico_completado_taller()` method for completed diagnostics
  - Add `obtener_tokens_usuarios_taller()` helper method to get all workshop user tokens
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 13.1, 13.2, 13.3, 13.4, 14.1, 14.2, 14.3, 14.4_

- [x] 2.2 Implement client notification methods in NotificationService
  - Add `notificar_tecnico_asignado()` method for technician assignment
  - Enhance existing `notificar_cambio_estado_servicio()` to handle all status transitions
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 17.1, 17.2, 17.3, 18.1, 18.2, 18.3, 19.1, 19.2, 19.3_

- [x] 2.3 Implement token lifecycle management methods
  - Add `limpiar_tokens_inactivos()` method to remove tokens inactive for 90+ days
  - Add `validar_y_limpiar_token()` method to validate tokens with FCM
  - Update `enviar_notificacion_push()` to handle invalid token errors (404, 400)
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 23.3, 23.4, 23.5, 24.4_

- [ ]* 2.4 Write unit tests for NotificationService methods
  - Test successful notification sending
  - Test invalid token handling (404 response)
  - Test retry logic with exponential backoff
  - Test multi-device token retrieval
  - File: `P2-backend/tests/services/test_notification_service.py`
  - _Requirements: 22.5, 23.5, 24.1, 24.2, 24.3_

### 3. Backend: Error Handling and Retry Logic

- [x] 3.1 Implement FCM error handler class
  - Create `FCMErrorHandler` class with `handle_fcm_error()` method
  - Handle error codes: 404 (invalid token), 400 (bad request), 401 (auth error), 429 (rate limit), 5xx (server errors)
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 24.1, 24.2, 24.4_

- [x] 3.2 Implement retry logic with exponential backoff
  - Create `enviar_notificacion_con_reintentos()` function with max 3 attempts
  - Implement exponential backoff: 1s, 2s, 4s delays
  - Handle timeout exceptions and retry
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 24.2, 24.3_

- [x] 3.3 Implement graceful degradation wrapper
  - Create `notificar_con_fallback()` function that catches all exceptions
  - Log failures without raising exceptions
  - Return boolean success status
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 24.3, 24.5_

### 4. Backend: Logging and Monitoring

- [x] 4.1 Implement structured logging for notifications
  - Create `NotificationLogger` class with methods: `log_notification_sent()`, `log_notification_failed()`, `log_token_registered()`, `log_token_removed()`
  - Use structured logging with JSON extra fields
  - File: `P2-backend/app/services/notification_service.py`
  - _Requirements: 25.1, 25.2, 25.3, 25.4_

- [ ] 4.2 Create health check endpoint
  - Add `GET /api/v1/notifications/health` endpoint
  - Check FCM credentials, access token, and database connectivity
  - Return status: "healthy", "degraded", or "unhealthy"
  - File: `P2-backend/app/api/api_v1/endpoints/notifications.py`
  - _Requirements: 24.5, 25.5_

### 5. Backend: Endpoint Enhancements

- [ ] 5.1 Update token registration endpoint
  - Modify `POST /notifications/register-token` to accept optional `plataforma` parameter
  - Update `fecha_ultima_actividad` on each registration
  - Handle token reassignment when token exists for different user
  - File: `P2-backend/app/api/api_v1/endpoints/notifications.py`
  - _Requirements: 2.3, 22.1, 22.2, 23.1, 23.2_

- [ ] 5.2 Update token unregistration endpoint
  - Modify `DELETE /notifications/unregister-token` to mark token as inactive instead of deleting
  - Set `activo = False` and update `fecha_ultima_actividad`
  - File: `P2-backend/app/api/api_v1/endpoints/notifications.py`
  - _Requirements: 2.5, 23.3_

### 6. Backend: Integration with Service Endpoints

- [ ] 6.1 Integrate notifications into service request creation
  - Add notification call in `crear_solicitudes_servicio_automaticas()` and `crear_solicitud_servicio_manual()`
  - Call `notificar_nueva_solicitud_taller()` after creating SolicitudServicio
  - File: `P2-backend/app/services/solicitud_servicio_service.py`
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 6.2 Integrate notifications into service request cancellation
  - Add notification call when client cancels service request
  - Call `notificar_solicitud_cancelada_taller()` after updating estado to "cancelado"
  - File: `P2-backend/app/api/api_v1/endpoints/servicios.py`
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 6.3 Integrate notifications into service acceptance
  - Add notification call when workshop accepts service request
  - Call `notificar_solicitud_aceptada()` after creating Servicio
  - File: `P2-backend/app/api/api_v1/endpoints/taller_servicios.py`
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 6.4 Integrate notifications into technician assignment
  - Add notification call when technician is assigned to service
  - Call `notificar_tecnico_asignado()` after assigning technician
  - File: `P2-backend/app/api/api_v1/endpoints/taller_servicios.py`
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [ ] 6.5 Integrate notifications into service status changes
  - Add notification calls for status changes: "en_camino", "en_lugar", "en_atencion"
  - Call `notificar_cambio_estado_servicio()` after updating Servicio.estado
  - File: `P2-backend/app/api/api_v1/endpoints/tecnico_servicios.py`
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 18.1, 18.2, 18.3, 18.4, 18.5, 19.1, 19.2, 19.3, 19.4, 19.5_

- [ ] 6.6 Integrate notifications into service completion
  - Add notification call when service is marked as "finalizado"
  - Call `notificar_servicio_finalizado()` after status update
  - File: `P2-backend/app/api/api_v1/endpoints/tecnico_servicios.py`
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

- [ ] 6.7 Integrate notifications into diagnostic completion
  - Add notification call when diagnostic is completed
  - Call `notificar_diagnostico_completado_taller()` after marking diagnostic complete
  - File: `P2-backend/app/api/api_v1/endpoints/diagnosticos.py`
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ]* 6.8 Write integration tests for notification triggers
  - Test notification sent when service request created
  - Test notification sent when service accepted
  - Test notification sent when status changes
  - File: `P2-backend/tests/api/test_notification_integration.py`
  - _Requirements: 12.5, 15.5, 17.5_

### 7. Checkpoint - Backend Complete

- [ ] 7. Ensure all backend tests pass and notifications are working
  - Run all unit tests: `pytest P2-backend/tests/`
  - Test notification endpoints manually using Postman or curl
  - Verify database schema changes applied correctly
  - Ensure all tests pass, ask the user if questions arise.

### 8. Mobile: Navigation Integration

- [ ] 8.1 Add navigator key management to NotificationService
  - Add static `GlobalKey<NavigatorState>? _navigatorKey` field
  - Add `setNavigatorKey()` method to set navigator key
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 8.2 Implement navigation methods in NotificationService
  - Implement `_navigateToServiceDetail()` method for service detail navigation
  - Implement `_navigateToRating()` method for rating screen navigation
  - Implement `_navigateToHome()` method for home screen navigation
  - Update `_handleMessageTap()` to use actual navigation methods
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8.3 Implement foreground notification display
  - Update `_handleMessage()` to show in-app notification banner
  - Implement `_showInAppNotification()` using SnackBar or overlay
  - Add "Ver" action button to navigate to notification target
  - Auto-dismiss after 5 seconds
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 8.4 Integrate NotificationService with main app
  - Set navigator key in MyApp widget
  - Call `NotificationService.setNavigatorKey()` with app's navigator key
  - Ensure background message handler is registered before runApp()
  - File: `P2-mobile/lib/main.dart`
  - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2, 4.3_

- [ ] 8.5 Add notification handling to login flow
  - Call `NotificationService.initialize()` after successful login
  - File: `P2-mobile/lib/screens/auth/login_screen.dart`
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 8.6 Add notification cleanup to logout flow
  - Call `NotificationService.unregisterToken()` before clearing session
  - File: `P2-mobile/lib/services/auth_service.dart`
  - _Requirements: 2.5_

- [ ]* 8.7 Write widget tests for notification navigation
  - Test navigation to service detail screen
  - Test navigation to rating screen
  - Test foreground notification display
  - File: `P2-mobile/test/services/notification_service_test.dart`
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

### 9. Mobile: Error Handling Enhancements

- [ ] 9.1 Implement permission denial handling
  - Store permission denial in local storage
  - Avoid repeated permission requests
  - Continue app operation without notifications
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 2.6_

- [ ] 9.2 Implement token registration retry logic
  - Add retry logic with exponential backoff (max 3 attempts)
  - Handle timeout exceptions
  - Check network connectivity before registration
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 2.3, 2.4_

- [ ] 9.3 Add connectivity checking
  - Implement `_checkConnectivity()` method
  - Schedule token registration retry when connectivity restored
  - File: `P2-mobile/lib/services/notification_service.dart`
  - _Requirements: 2.3_

### 10. Checkpoint - Mobile Complete

- [ ] 10. Ensure mobile app notifications are working end-to-end
  - Test foreground notification display
  - Test background notification handling
  - Test notification navigation to all screens
  - Test token registration and unregistration
  - Ensure all tests pass, ask the user if questions arise.

### 11. Web: Firebase SDK Integration

- [ ] 11.1 Install Firebase dependencies
  - Add `firebase` package to package.json
  - Run `npm install` to install dependencies
  - File: `P2-frontend/package.json`
  - _Requirements: 6.1, 6.2_

- [ ] 11.2 Create Firebase module
  - Create `FirebaseModule` that initializes Firebase app
  - Initialize Firebase with config from `firebase.config.ts`
  - Initialize Firebase Messaging
  - File: `P2-frontend/src/app/core/firebase/firebase.module.ts`
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 11.3 Verify browser support for notifications
  - Check for `Notification` API support
  - Check for `serviceWorker` API support
  - Check for secure context (HTTPS)
  - Display user-friendly error messages for unsupported browsers
  - File: `P2-frontend/src/app/core/firebase/firebase.module.ts`
  - _Requirements: 6.5_

### 12. Web: Service Worker Implementation

- [ ] 12.1 Create Firebase Messaging Service Worker
  - Create `firebase-messaging-sw.js` in public folder
  - Import Firebase scripts using `importScripts()`
  - Initialize Firebase in Service Worker context
  - File: `P2-frontend/public/firebase-messaging-sw.js`
  - _Requirements: 7.1, 7.2_

- [ ] 12.2 Implement background message handler
  - Implement `onBackgroundMessage()` handler
  - Display browser notification with title, body, icon, and badge
  - Include notification data for click handling
  - File: `P2-frontend/public/firebase-messaging-sw.js`
  - _Requirements: 7.3, 11.2_

- [ ] 12.3 Implement notification click handler
  - Add `notificationclick` event listener
  - Close notification on click
  - Focus existing window or open new window
  - Navigate to appropriate route based on notification action
  - File: `P2-frontend/public/firebase-messaging-sw.js`
  - _Requirements: 7.4, 11.3, 11.4, 28.1, 28.2, 28.3, 28.4_

- [ ] 12.4 Register Service Worker in main.ts
  - Register Service Worker after app bootstrap
  - Handle registration success and failure
  - File: `P2-frontend/src/main.ts`
  - _Requirements: 7.1, 7.5_

### 13. Web: NotificationService Implementation

- [ ] 13.1 Create NotificationService class
  - Create Angular service with Firebase Messaging integration
  - Add properties: `messaging`, `notificationSubject`, `notification$`, `permissionStatus`, `currentToken`
  - Inject HttpClient for backend communication
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 26.1, 26.2, 26.4_

- [ ] 13.2 Implement permission request method
  - Implement `requestPermission()` method
  - Check browser support before requesting
  - Request notification permissions from user
  - Call `registerToken()` on permission granted
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 13.3 Implement token registration method
  - Implement `registerToken()` private method
  - Get FCM token using `getToken()` with VAPID key
  - Call `sendTokenToBackend()` with token
  - Setup message listener after registration
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 9.1, 9.2, 9.3_

- [ ] 13.4 Implement backend token registration with retry
  - Implement `sendTokenToBackend()` method with retry logic
  - POST token to `/notifications/register-token` endpoint
  - Retry up to 3 times with exponential backoff on failure
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 9.3, 9.5_

- [ ] 13.5 Implement foreground message listener
  - Implement `setupMessageListener()` method
  - Use `onMessage()` to listen for foreground messages
  - Emit notification through `notificationSubject`
  - Play notification sound
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 10.1, 10.2, 10.3_

- [ ] 13.6 Implement token unregistration method
  - Implement `unregisterToken()` method
  - DELETE token from backend via `/notifications/unregister-token`
  - Clear `currentToken` on success
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 9.4_

- [ ] 13.7 Implement utility methods
  - Implement `playNotificationSound()` method
  - Implement `getPermissionStatus()` method
  - Implement `refreshToken()` method
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 10.3, 26.4, 26.5, 30.4_

### 14. Web: Notification UI Components

- [ ] 14.1 Create NotificationToast component
  - Create component with template for displaying notifications
  - Add properties: `notifications` array, `subscription`
  - Inject NotificationService and Router
  - File: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts`
  - _Requirements: 27.1, 27.2_

- [ ] 14.2 Implement notification display logic
  - Subscribe to `notification$` observable in `ngOnInit()`
  - Add notifications to array when received
  - Auto-dismiss notifications after 8 seconds
  - File: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts`
  - _Requirements: 10.1, 10.2, 10.5, 27.5_

- [ ] 14.3 Implement notification click handling
  - Implement `handleNotificationClick()` method
  - Navigate to appropriate route based on notification action
  - Dismiss notification after click
  - File: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts`
  - _Requirements: 10.4, 28.1, 28.2, 28.3, 28.4, 28.5_

- [ ] 14.4 Implement notification dismissal
  - Implement `dismissNotification()` method
  - Remove notification from array
  - File: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts`
  - _Requirements: 27.3_

- [ ] 14.5 Style NotificationToast component
  - Add CSS styles for notification container, toast, icon, content, and actions
  - Implement slide-in animation
  - Make notifications stack vertically
  - File: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts`
  - _Requirements: 27.2, 27.4, 27.5_

### 15. Web: App Integration

- [ ] 15.1 Import FirebaseModule in AppModule
  - Add FirebaseModule to imports array
  - Add NotificationService to providers array
  - File: `P2-frontend/src/app/app.module.ts`
  - _Requirements: 6.1, 6.2, 26.1_

- [ ] 15.2 Add NotificationToast to AppComponent
  - Add `<app-notification-toast>` to AppComponent template
  - File: `P2-frontend/src/app/app.component.ts`
  - _Requirements: 27.1_

- [ ] 15.3 Integrate notifications with login flow
  - Call `notificationService.requestPermission()` after successful login
  - Subscribe to `authService.currentUser$` to detect login
  - File: `P2-frontend/src/app/app.component.ts`
  - _Requirements: 8.1, 8.2, 8.3, 9.1, 9.2_

- [ ] 15.4 Integrate notifications with logout flow
  - Call `notificationService.unregisterToken()` on logout
  - File: `P2-frontend/src/app/core/services/auth.service.ts`
  - _Requirements: 9.4_

- [ ] 15.5 Add Service Worker message listener
  - Listen for Service Worker messages in AppComponent
  - Handle `NOTIFICATION_CLICK` messages from Service Worker
  - Navigate to URL provided in message
  - File: `P2-frontend/src/app/app.component.ts`
  - _Requirements: 7.4, 11.4, 28.5_

### 16. Web: Error Handling

- [ ] 16.1 Implement browser compatibility checks
  - Check for Notification API support
  - Check for Service Worker support
  - Check for secure context (HTTPS)
  - Display user-friendly error messages
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 6.5_

- [ ] 16.2 Implement Service Worker registration error handling
  - Handle Service Worker registration failure
  - Fallback to foreground-only mode
  - Log errors for debugging
  - File: `P2-frontend/src/main.ts`
  - _Requirements: 7.1, 7.5_

- [ ] 16.3 Implement token refresh error handling
  - Handle permission blocked errors
  - Handle token subscription failures
  - Retry token registration with exponential backoff
  - File: `P2-frontend/src/app/core/services/notification.service.ts`
  - _Requirements: 9.5_

- [ ]* 16.4 Write unit tests for NotificationService
  - Test permission request flow
  - Test token registration and unregistration
  - Test foreground message handling
  - Test error handling scenarios
  - File: `P2-frontend/src/app/core/services/notification.service.spec.ts`
  - _Requirements: 8.5, 9.5, 26.1, 26.2_

### 17. Checkpoint - Web Complete

- [ ] 17. Ensure web app notifications are working end-to-end
  - Test permission request flow
  - Test foreground notification display
  - Test background notification display
  - Test notification click navigation
  - Test token registration and unregistration
  - Ensure all tests pass, ask the user if questions arise.

### 18. Cross-Platform Testing and Validation

- [ ] 18.1 Test multi-device token management
  - Register multiple devices for same user
  - Verify all devices receive notifications
  - Test token reassignment when device switches users
  - _Requirements: 22.1, 22.2, 22.3, 22.4_

- [ ] 18.2 Test notification delivery across all platforms
  - Send test notifications from backend to mobile devices
  - Send test notifications from backend to web browsers
  - Verify notification content and data payload
  - _Requirements: 12.3, 15.3, 16.3, 17.3, 18.3, 19.3, 20.3_

- [ ] 18.3 Test notification navigation on all platforms
  - Test navigation from notifications on mobile app
  - Test navigation from notifications on web app
  - Verify correct screens/routes are opened
  - _Requirements: 5.1, 5.2, 5.3, 28.1, 28.2, 28.3, 28.4_

- [ ] 18.4 Test error handling and recovery
  - Test invalid token removal
  - Test retry logic with network failures
  - Test graceful degradation when FCM unavailable
  - _Requirements: 23.5, 24.1, 24.2, 24.3, 24.4_

- [ ] 18.5 Test token lifecycle management
  - Test token registration on login
  - Test token unregistration on logout
  - Test token reassignment between users
  - Verify inactive token cleanup
  - _Requirements: 23.1, 23.2, 23.3, 23.4_

### 19. Documentation and Deployment Preparation

- [ ] 19.1 Document notification payload structure
  - Create documentation for all notification types
  - Document data payload fields for each notification
  - Document notification actions and navigation targets
  - File: `P2-backend/docs/notifications.md`
  - _Requirements: All notification requirements_

- [ ] 19.2 Create deployment checklist
  - Document Firebase configuration requirements
  - Document environment variables needed
  - Document database migration steps
  - Document Service Worker deployment requirements
  - File: `P2-backend/docs/deployment.md`
  - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.2, 7.1_

- [ ] 19.3 Update API documentation
  - Document notification endpoints in OpenAPI/Swagger
  - Document notification trigger events
  - Document error responses
  - File: `P2-backend/app/api/api_v1/endpoints/notifications.py`
  - _Requirements: All API requirements_

- [ ] 19.4 Create monitoring and alerting guide
  - Document how to monitor notification success rates
  - Document how to use health check endpoint
  - Document log analysis for troubleshooting
  - File: `P2-backend/docs/monitoring.md`
  - _Requirements: 24.5, 25.1, 25.2, 25.3, 25.4, 25.5_

### 20. Final Checkpoint - System Complete

- [ ] 20. Final validation and handoff
  - Run all tests across all platforms
  - Verify all requirements are met
  - Verify all notification types are working
  - Verify error handling and logging
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Backend tasks should be completed before mobile and web tasks
- Mobile and web tasks can be done in parallel after backend is complete
- Checkpoints ensure incremental validation at major milestones
- All notification methods include proper error handling and logging
- Token lifecycle management ensures database cleanliness
- Multi-device support is built into the architecture from the start
