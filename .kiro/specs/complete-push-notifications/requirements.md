# Requirements Document: Complete Push Notifications Implementation

## Introduction

This document specifies the requirements for completing the push notifications implementation across a vehicle assistance platform consisting of three components: P2-backend (FastAPI), P2-mobile (Flutter), and Frontend (Angular web app). The backend has partial FCM API v1 integration, the mobile app has a complete notification service implementation, and the web app requires full Firebase integration from scratch.

The system enables real-time communication between clients/drivers (mobile app) and workshop staff (web app) regarding service requests, status updates, and technician assignments.

## Glossary

- **FCM**: Firebase Cloud Messaging - Google's push notification service
- **P2_Backend**: FastAPI backend service that manages notifications and stores device tokens
- **P2_Mobile**: Flutter mobile application used by clients/drivers
- **Frontend_Web**: Angular web application used by workshop/taller staff
- **Device_Token**: FCM registration token that uniquely identifies a device for push notifications
- **Notification_Service**: Backend service that sends push notifications via FCM API v1
- **Service_Worker**: Background script that handles push notifications in web browsers
- **Foreground_Notification**: Notification received while the app is active and visible
- **Background_Notification**: Notification received while the app is not active
- **Taller**: Workshop that provides vehicle assistance services
- **Técnico**: Technician assigned to provide on-site vehicle assistance
- **Cliente**: Client/driver requesting vehicle assistance
- **Solicitud_Servicio**: Service request created by a client

## Requirements

### Requirement 1: Backend Firebase Configuration

**User Story:** As a system administrator, I want the backend to have proper Firebase credentials configured, so that push notifications can be sent reliably.

#### Acceptance Criteria

1. THE P2_Backend SHALL load Firebase credentials from a valid firebase-credentials.json file
2. WHEN the firebase-credentials.json file is missing, THE P2_Backend SHALL log a descriptive error message and disable notification features
3. THE P2_Backend SHALL use consistent Firebase project IDs across all environment variables
4. THE P2_Backend SHALL validate Firebase credentials on startup
5. WHEN Firebase credentials are invalid, THE P2_Backend SHALL log the validation error and continue operation without notification features

### Requirement 2: Mobile App Token Registration

**User Story:** As a mobile app user, I want my device to automatically register for notifications when I log in, so that I receive service updates.

#### Acceptance Criteria

1. WHEN a user successfully logs in, THE P2_Mobile SHALL request notification permissions from the operating system
2. WHEN notification permissions are granted, THE P2_Mobile SHALL obtain an FCM device token
3. WHEN an FCM device token is obtained, THE P2_Mobile SHALL send the token to P2_Backend via the /notifications/register-token endpoint
4. WHEN the FCM token is refreshed by Firebase, THE P2_Mobile SHALL automatically send the updated token to P2_Backend
5. WHEN a user logs out, THE P2_Mobile SHALL send the device token to P2_Backend via the /notifications/unregister-token endpoint
6. WHEN notification permissions are denied, THE P2_Mobile SHALL continue normal operation without notification features

### Requirement 3: Mobile App Foreground Notification Handling

**User Story:** As a mobile app user, I want to see notifications while using the app, so that I stay informed of service updates in real-time.

#### Acceptance Criteria

1. WHEN a push notification is received and P2_Mobile is in the foreground, THE P2_Mobile SHALL display an in-app notification banner
2. THE P2_Mobile SHALL display the notification title and body text in the banner
3. WHEN a user taps the in-app notification banner, THE P2_Mobile SHALL navigate to the appropriate screen based on the notification type
4. THE P2_Mobile SHALL automatically dismiss the in-app notification banner after 5 seconds
5. WHEN multiple notifications are received in foreground, THE P2_Mobile SHALL queue and display them sequentially

### Requirement 4: Mobile App Background Notification Handling

**User Story:** As a mobile app user, I want to receive notifications when the app is closed or in the background, so that I don't miss important service updates.

#### Acceptance Criteria

1. WHEN a push notification is received and P2_Mobile is in the background, THE operating system SHALL display a system notification
2. WHEN a push notification is received and P2_Mobile is terminated, THE operating system SHALL display a system notification
3. WHEN a user taps a system notification, THE P2_Mobile SHALL launch and navigate to the appropriate screen based on the notification data
4. THE P2_Mobile SHALL handle notification taps even when the app was completely closed
5. THE P2_Mobile SHALL process background notifications without requiring the app to be running

### Requirement 5: Mobile App Notification Navigation

**User Story:** As a mobile app user, I want to be taken to the relevant screen when I tap a notification, so that I can quickly view the details.

#### Acceptance Criteria

1. WHEN a notification with action "abrir_servicio_detalle" is tapped, THE P2_Mobile SHALL navigate to the service detail screen with the provided servicio_id
2. WHEN a notification with action "abrir_valoracion" is tapped, THE P2_Mobile SHALL navigate to the service rating screen with the provided servicio_id
3. WHEN a notification with an unknown action is tapped, THE P2_Mobile SHALL navigate to the home screen
4. WHEN a notification is tapped and the user is not logged in, THE P2_Mobile SHALL navigate to the login screen
5. THE P2_Mobile SHALL preserve the notification data during navigation

### Requirement 6: Web App Firebase SDK Integration

**User Story:** As a workshop staff member, I want the web app to support push notifications, so that I can receive alerts about new service requests.

#### Acceptance Criteria

1. THE Frontend_Web SHALL include the Firebase JavaScript SDK as a dependency
2. THE Frontend_Web SHALL initialize Firebase with valid project configuration on application startup
3. WHEN Firebase initialization fails, THE Frontend_Web SHALL log the error and continue operation without notification features
4. THE Frontend_Web SHALL configure Firebase Messaging with the correct sender ID and VAPID key
5. THE Frontend_Web SHALL verify browser support for push notifications before attempting to register

### Requirement 7: Web App Service Worker Configuration

**User Story:** As a workshop staff member, I want the web app to handle notifications in the background, so that I receive alerts even when the browser tab is not active.

#### Acceptance Criteria

1. THE Frontend_Web SHALL register a Service Worker for handling FCM messages
2. THE Service Worker SHALL listen for push events from FCM
3. WHEN a push event is received, THE Service Worker SHALL display a browser notification
4. WHEN a browser notification is clicked, THE Service Worker SHALL focus or open the Frontend_Web and navigate to the appropriate route
5. THE Service Worker SHALL remain active even when all browser tabs are closed

### Requirement 8: Web App Notification Permission Request

**User Story:** As a workshop staff member, I want to be asked for notification permissions, so that I can choose to receive push notifications.

#### Acceptance Criteria

1. WHEN a user logs in to Frontend_Web, THE Frontend_Web SHALL check the current notification permission status
2. WHEN notification permissions are "default" (not yet requested), THE Frontend_Web SHALL display a permission request dialog
3. WHEN the user grants notification permissions, THE Frontend_Web SHALL obtain an FCM device token
4. WHEN the user denies notification permissions, THE Frontend_Web SHALL store the denial and not request again for 7 days
5. THE Frontend_Web SHALL provide a settings option to manually request notification permissions again

### Requirement 9: Web App Token Registration

**User Story:** As a workshop staff member, I want my browser to automatically register for notifications when I log in, so that I receive service request alerts.

#### Acceptance Criteria

1. WHEN a user successfully logs in and notification permissions are granted, THE Frontend_Web SHALL obtain an FCM device token
2. WHEN an FCM device token is obtained, THE Frontend_Web SHALL send the token to P2_Backend via the /notifications/register-token endpoint
3. WHEN the FCM token is refreshed by Firebase, THE Frontend_Web SHALL automatically send the updated token to P2_Backend
4. WHEN a user logs out, THE Frontend_Web SHALL send the device token to P2_Backend via the /notifications/unregister-token endpoint
5. WHEN token registration fails, THE Frontend_Web SHALL retry up to 3 times with exponential backoff

### Requirement 10: Web App Foreground Notification Display

**User Story:** As a workshop staff member, I want to see notifications while using the web app, so that I'm immediately aware of new service requests.

#### Acceptance Criteria

1. WHEN a push notification is received and Frontend_Web is in the foreground, THE Frontend_Web SHALL display an in-app notification toast
2. THE Frontend_Web SHALL display the notification title, body, and a dismiss button in the toast
3. THE Frontend_Web SHALL play a notification sound when displaying the toast
4. WHEN a user clicks the notification toast, THE Frontend_Web SHALL navigate to the appropriate route based on the notification type
5. THE Frontend_Web SHALL automatically dismiss the notification toast after 8 seconds

### Requirement 11: Web App Background Notification Display

**User Story:** As a workshop staff member, I want to receive browser notifications when the web app is not active, so that I don't miss urgent service requests.

#### Acceptance Criteria

1. WHEN a push notification is received and Frontend_Web is not in the foreground, THE Service Worker SHALL display a browser notification
2. THE browser notification SHALL include the notification title, body, and an icon
3. WHEN a user clicks the browser notification, THE Service Worker SHALL focus the Frontend_Web tab or open a new tab
4. WHEN the Frontend_Web tab is focused from a notification click, THE Frontend_Web SHALL navigate to the appropriate route based on the notification data
5. THE browser notification SHALL remain visible until the user dismisses it or clicks it

### Requirement 12: Backend Notification for Workshop - New Service Request

**User Story:** As a workshop staff member, I want to receive a push notification when a new service request is created, so that I can respond quickly.

#### Acceptance Criteria

1. WHEN a new Solicitud_Servicio is created, THE P2_Backend SHALL identify all workshop users associated with the target taller
2. THE P2_Backend SHALL retrieve all device tokens for the identified workshop users
3. THE P2_Backend SHALL send a push notification with title "Nueva Solicitud de Servicio" and the client's location details
4. THE notification data SHALL include tipo="nueva_solicitud", solicitud_id, and accion="abrir_solicitud_detalle"
5. WHEN no device tokens are found for the workshop, THE P2_Backend SHALL log the event and continue without error

### Requirement 13: Backend Notification for Workshop - Service Cancellation

**User Story:** As a workshop staff member, I want to receive a notification when a client cancels a service request, so that I can reassign resources.

#### Acceptance Criteria

1. WHEN a Solicitud_Servicio is cancelled by a client, THE P2_Backend SHALL identify all workshop users associated with the taller
2. THE P2_Backend SHALL retrieve all device tokens for the identified workshop users
3. THE P2_Backend SHALL send a push notification with title "Solicitud Cancelada" and the cancellation reason
4. THE notification data SHALL include tipo="solicitud_cancelada", solicitud_id, and accion="abrir_solicitudes_lista"
5. THE P2_Backend SHALL send the notification within 5 seconds of the cancellation event

### Requirement 14: Backend Notification for Workshop - Diagnostic Completed

**User Story:** As a workshop staff member, I want to receive a notification when a diagnostic is completed, so that I can review and approve the service.

#### Acceptance Criteria

1. WHEN a Diagnostico is marked as completed, THE P2_Backend SHALL identify all workshop users associated with the taller
2. THE P2_Backend SHALL retrieve all device tokens for the identified workshop users
3. THE P2_Backend SHALL send a push notification with title "Diagnóstico Completado" and the diagnostic summary
4. THE notification data SHALL include tipo="diagnostico_completado", diagnostico_id, and accion="abrir_diagnostico_detalle"
5. THE P2_Backend SHALL include the técnico name in the notification body

### Requirement 15: Backend Notification for Client - Request Accepted

**User Story:** As a client, I want to receive a notification when a workshop accepts my service request, so that I know help is on the way.

#### Acceptance Criteria

1. WHEN a taller accepts a Solicitud_Servicio, THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "¡Solicitud Aceptada!" and the taller name
3. THE notification data SHALL include tipo="solicitud_aceptada", servicio_id, and accion="abrir_servicio_detalle"
4. THE P2_Backend SHALL include the estimated arrival time in the notification body if available
5. THE P2_Backend SHALL send the notification within 3 seconds of the acceptance event

### Requirement 16: Backend Notification for Client - Technician Assigned

**User Story:** As a client, I want to receive a notification when a technician is assigned to my service, so that I know who is coming to help.

#### Acceptance Criteria

1. WHEN a técnico is assigned to a Servicio, THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "Técnico Asignado" and the técnico's name
3. THE notification data SHALL include tipo="tecnico_asignado", servicio_id, tecnico_id, and accion="abrir_servicio_detalle"
4. THE P2_Backend SHALL include the técnico's phone number in the notification body
5. THE P2_Backend SHALL send the notification immediately after the assignment

### Requirement 17: Backend Notification for Client - Technician En Route

**User Story:** As a client, I want to receive a notification when the technician is on the way, so that I can prepare for their arrival.

#### Acceptance Criteria

1. WHEN a Servicio status changes to "en_camino", THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "Técnico en Camino" and the estimated arrival time
3. THE notification data SHALL include tipo="tecnico_en_camino", servicio_id, and accion="abrir_servicio_detalle"
4. THE P2_Backend SHALL include the técnico's current location in the notification data
5. THE P2_Backend SHALL send the notification within 3 seconds of the status change

### Requirement 18: Backend Notification for Client - Technician Arrived

**User Story:** As a client, I want to receive a notification when the technician arrives at my location, so that I can meet them.

#### Acceptance Criteria

1. WHEN a Servicio status changes to "en_lugar", THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "Técnico en el Lugar" and a message to meet the technician
3. THE notification data SHALL include tipo="tecnico_en_lugar", servicio_id, and accion="abrir_servicio_detalle"
4. THE P2_Backend SHALL include the técnico's phone number in the notification body
5. THE P2_Backend SHALL send the notification immediately upon status change

### Requirement 19: Backend Notification for Client - Service In Progress

**User Story:** As a client, I want to receive a notification when the technician starts working on my vehicle, so that I'm aware of the service progress.

#### Acceptance Criteria

1. WHEN a Servicio status changes to "en_atencion", THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "Servicio en Atención" and a progress message
3. THE notification data SHALL include tipo="servicio_en_atencion", servicio_id, and accion="abrir_servicio_detalle"
4. THE P2_Backend SHALL include the estimated completion time in the notification body if available
5. THE P2_Backend SHALL send the notification within 3 seconds of the status change

### Requirement 20: Backend Notification for Client - Service Completed

**User Story:** As a client, I want to receive a notification when my service is completed, so that I can rate the experience and proceed with payment.

#### Acceptance Criteria

1. WHEN a Servicio status changes to "finalizado", THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "¡Servicio Completado!" and a prompt to rate the service
3. THE notification data SHALL include tipo="servicio_finalizado", servicio_id, and accion="abrir_valoracion"
4. THE P2_Backend SHALL include the total service cost in the notification body
5. THE P2_Backend SHALL send the notification immediately upon service completion

### Requirement 21: Backend Notification for Client - Service Cancelled

**User Story:** As a client, I want to receive a notification if my service is cancelled by the workshop, so that I can request assistance from another provider.

#### Acceptance Criteria

1. WHEN a Servicio status changes to "cancelado" by the taller, THE P2_Backend SHALL retrieve all device tokens for the client
2. THE P2_Backend SHALL send a push notification with title "Servicio Cancelado" and the cancellation reason
3. THE notification data SHALL include tipo="servicio_cancelado", servicio_id, and accion="abrir_solicitudes_lista"
4. THE P2_Backend SHALL include contact information for customer support in the notification body
5. THE P2_Backend SHALL send the notification within 3 seconds of the cancellation

### Requirement 22: Multi-Device Token Management

**User Story:** As a user with multiple devices, I want all my devices to receive notifications, so that I stay informed regardless of which device I'm using.

#### Acceptance Criteria

1. THE P2_Backend SHALL store multiple device tokens per user in the DispositivoUsuario table
2. WHEN sending a notification, THE P2_Backend SHALL retrieve all active device tokens for the target user
3. THE P2_Backend SHALL send the notification to all retrieved device tokens
4. WHEN a device token is invalid or expired, THE P2_Backend SHALL remove it from the database
5. THE P2_Backend SHALL log the number of successful and failed notification deliveries per user

### Requirement 23: Token Lifecycle Management

**User Story:** As a system administrator, I want device tokens to be properly managed throughout their lifecycle, so that the database remains clean and notifications are reliable.

#### Acceptance Criteria

1. WHEN a device token is registered, THE P2_Backend SHALL check if the token already exists in the database
2. WHEN a token already exists for a different user, THE P2_Backend SHALL reassign the token to the current user
3. WHEN a user logs out, THE P2_Backend SHALL mark the device token as inactive rather than deleting it
4. THE P2_Backend SHALL automatically remove device tokens that have been inactive for more than 90 days
5. WHEN FCM returns an "invalid token" error, THE P2_Backend SHALL immediately remove the token from the database

### Requirement 24: Notification Error Handling

**User Story:** As a system administrator, I want notification failures to be handled gracefully, so that the system remains stable even when FCM is unavailable.

#### Acceptance Criteria

1. WHEN FCM API returns an error, THE P2_Backend SHALL log the error details including the HTTP status code and response body
2. WHEN FCM API is unreachable, THE P2_Backend SHALL retry the notification up to 3 times with exponential backoff
3. WHEN all retry attempts fail, THE P2_Backend SHALL log the failure and continue operation without throwing an exception
4. WHEN a notification fails for a specific token, THE P2_Backend SHALL continue sending to remaining tokens
5. THE P2_Backend SHALL expose a health check endpoint that reports FCM connectivity status

### Requirement 25: Notification Logging and Monitoring

**User Story:** As a system administrator, I want all notification events to be logged, so that I can monitor system performance and troubleshoot issues.

#### Acceptance Criteria

1. THE P2_Backend SHALL log every notification send attempt with timestamp, recipient user ID, notification type, and result
2. THE P2_Backend SHALL log the number of device tokens targeted for each notification
3. THE P2_Backend SHALL log the FCM response for each notification including success and failure counts
4. WHEN a notification fails, THE P2_Backend SHALL log the error message and affected device token
5. THE P2_Backend SHALL provide a metrics endpoint that reports notification success rate, failure rate, and average delivery time

### Requirement 26: Web App Notification Service

**User Story:** As a developer, I want a centralized notification service in the web app, so that notification logic is reusable and maintainable.

#### Acceptance Criteria

1. THE Frontend_Web SHALL implement a NotificationService that encapsulates all Firebase Messaging logic
2. THE NotificationService SHALL provide methods for requesting permissions, registering tokens, and handling messages
3. THE NotificationService SHALL emit events when notifications are received that other components can subscribe to
4. THE NotificationService SHALL maintain the current notification permission state
5. THE NotificationService SHALL provide a method to manually refresh the FCM token

### Requirement 27: Web App Notification UI Component

**User Story:** As a workshop staff member, I want a consistent notification display in the web app, so that all notifications look professional and are easy to interact with.

#### Acceptance Criteria

1. THE Frontend_Web SHALL implement a NotificationToast component for displaying foreground notifications
2. THE NotificationToast SHALL display the notification icon, title, body, and timestamp
3. THE NotificationToast SHALL provide action buttons based on the notification type
4. THE NotificationToast SHALL support dismissing notifications with a close button
5. THE NotificationToast SHALL stack multiple notifications vertically when multiple are received

### Requirement 28: Web App Notification Routing

**User Story:** As a workshop staff member, I want to be taken to the relevant page when I click a notification, so that I can quickly respond to service requests.

#### Acceptance Criteria

1. WHEN a notification with accion="abrir_solicitud_detalle" is clicked, THE Frontend_Web SHALL navigate to the service request detail page with the provided solicitud_id
2. WHEN a notification with accion="abrir_diagnostico_detalle" is clicked, THE Frontend_Web SHALL navigate to the diagnostic detail page with the provided diagnostico_id
3. WHEN a notification with accion="abrir_solicitudes_lista" is clicked, THE Frontend_Web SHALL navigate to the service requests list page
4. WHEN a notification with an unknown action is clicked, THE Frontend_Web SHALL navigate to the dashboard
5. THE Frontend_Web SHALL preserve the notification data in the route parameters for context

### Requirement 29: Notification Preferences

**User Story:** As a user, I want to control which types of notifications I receive, so that I'm only alerted about events that matter to me.

#### Acceptance Criteria

1. THE Frontend_Web and P2_Mobile SHALL provide a notification preferences screen
2. THE preferences screen SHALL allow users to enable or disable notifications by type (new requests, status updates, cancellations)
3. WHEN a user disables a notification type, THE P2_Backend SHALL not send notifications of that type to the user
4. THE P2_Backend SHALL store notification preferences in the database associated with the user account
5. THE notification preferences SHALL sync across all user devices

### Requirement 30: Notification Sound Configuration

**User Story:** As a user, I want to control notification sounds, so that I can customize my notification experience.

#### Acceptance Criteria

1. THE P2_Mobile SHALL allow users to enable or disable notification sounds in the app settings
2. THE Frontend_Web SHALL allow users to enable or disable notification sounds in the app settings
3. WHEN notification sounds are enabled, THE P2_Mobile SHALL play the default system notification sound
4. WHEN notification sounds are enabled, THE Frontend_Web SHALL play a custom notification sound file
5. THE sound preference SHALL be stored locally on each device

