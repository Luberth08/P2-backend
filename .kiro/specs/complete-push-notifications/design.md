# Design Document: Complete Push Notifications Implementation

## Overview

This design document specifies the technical implementation for completing push notifications across a vehicle assistance platform consisting of three components:

- **P2-backend**: FastAPI backend with partial FCM API v1 integration
- **P2-mobile**: Flutter mobile application with complete notification service
- **P2-frontend**: Angular web application requiring full Firebase integration

The system enables real-time bidirectional communication between clients/drivers (mobile app) and workshop staff (web app) regarding service requests, status updates, technician assignments, and service lifecycle events.

### Current State

**Backend (P2-backend)**:
- ✅ Firebase credentials configured (firebase-credentials.json)
- ✅ FCM API v1 integration with OAuth2 token management
- ✅ NotificationService with token management and basic notification sending
- ✅ DispositivoUsuario model for storing device tokens
- ✅ Endpoints: `/notifications/register-token`, `/notifications/unregister-token`, `/notifications/test-notification`
- ✅ Notifications for clients: solicitud_aceptada, cambio_estado_servicio, servicio_finalizado
- ❌ Missing: Notifications for workshop users (nueva_solicitud, solicitud_cancelada, diagnostico_completado)

**Mobile (P2-mobile)**:
- ✅ firebase_messaging dependency configured
- ✅ google-services.json configured for Android
- ✅ Complete NotificationService implementation with token registration, foreground/background handlers
- ⚠️ Navigation handlers are stubbed (need integration with actual navigation)

**Web (P2-frontend)**:
- ✅ firebase.config.ts with project configuration and VAPID key
- ❌ No Firebase SDK dependencies
- ❌ No Service Worker implementation
- ❌ No notification service
- ❌ No UI components for notifications

### Design Goals

1. **Complete Backend Notifications**: Implement missing workshop notification methods
2. **Enhance Mobile Navigation**: Connect notification handlers to actual navigation routes
3. **Implement Web Notifications**: Full Firebase integration from scratch including SDK, Service Worker, notification service, and UI components
4. **Ensure Reliability**: Implement proper error handling, retry logic, and token lifecycle management
5. **Maintain Consistency**: Ensure notification payloads and behaviors are consistent across platforms



## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        Mobile[P2-mobile Flutter App]
        Web[P2-frontend Angular App]
    end
    
    subgraph "Firebase Cloud Messaging"
        FCM[FCM API v1]
        FCMSDK[FCM SDK Mobile]
        FCMWEB[FCM SDK Web]
    end
    
    subgraph "Backend Layer"
        API[FastAPI Backend]
        NotifService[NotificationService]
        TokenDB[(DispositivoUsuario DB)]
    end
    
    subgraph "Service Worker Layer"
        SW[Service Worker]
    end
    
    Mobile -->|Register Token| API
    Mobile -->|Receive Push| FCMSDK
    FCMSDK -->|Token| Mobile
    
    Web -->|Register Token| API
    Web -->|Foreground Messages| FCMWEB
    SW -->|Background Messages| FCMWEB
    FCMWEB -->|Token| Web
    
    API -->|Store/Retrieve Tokens| TokenDB
    API -->|Send Notification| FCM
    NotifService -->|OAuth2 Token| FCM
    FCM -->|Push to Device| FCMSDK
    FCM -->|Push to Browser| FCMWEB
    
    style Mobile fill:#e1f5ff
    style Web fill:#fff4e1
    style API fill:#e8f5e9
    style FCM fill:#fce4ec
```

### Component Interaction Flow

#### Token Registration Flow

```mermaid
sequenceDiagram
    participant Client as Client (Mobile/Web)
    participant Firebase as Firebase SDK
    participant Backend as FastAPI Backend
    participant DB as Database
    
    Client->>Client: User logs in
    Client->>Firebase: Request notification permissions
    Firebase-->>Client: Permission granted/denied
    
    alt Permission Granted
        Client->>Firebase: Get FCM token
        Firebase-->>Client: Return token
        Client->>Backend: POST /notifications/register-token
        Backend->>DB: Check if token exists
        
        alt Token exists for different user
            Backend->>DB: Reassign token to current user
        else Token doesn't exist
            Backend->>DB: Create new DispositivoUsuario record
        end
        
        Backend-->>Client: Success response
    end
    
    Firebase->>Firebase: Token refresh event
    Firebase-->>Client: New token
    Client->>Backend: POST /notifications/register-token (updated token)
```

#### Notification Send Flow

```mermaid
sequenceDiagram
    participant Event as System Event
    participant Backend as NotificationService
    participant DB as Database
    participant FCM as FCM API v1
    participant Device as Client Device
    
    Event->>Backend: Trigger notification (e.g., new service request)
    Backend->>DB: Get user ID(s) for notification
    Backend->>DB: Get all device tokens for user(s)
    DB-->>Backend: Return tokens list
    
    loop For each token
        Backend->>Backend: Get OAuth2 access token
        Backend->>FCM: POST message with token
        
        alt Success
            FCM-->>Device: Push notification
            FCM-->>Backend: 200 OK
            Backend->>Backend: Log success
        else Invalid Token
            FCM-->>Backend: 404 Token not found
            Backend->>DB: Remove invalid token
        else Temporary Error
            FCM-->>Backend: 5xx Server error
            Backend->>Backend: Retry with exponential backoff
        end
    end
```

### Technology Stack

**Backend**:
- FastAPI (Python 3.11+)
- SQLAlchemy (async)
- google-auth library for OAuth2
- httpx for async HTTP requests
- Firebase Admin SDK credentials

**Mobile**:
- Flutter 3.11+
- firebase_core: ^2.24.2
- firebase_messaging: ^14.7.10
- flutter_local_notifications (for foreground display)

**Web**:
- Angular 21+
- Firebase JavaScript SDK v10+
- Service Worker API
- Notification API
- RxJS for reactive state management



## Components and Interfaces

### Backend Components

#### 1. NotificationService (Enhanced)

**Location**: `P2-backend/app/services/notification_service.py`

**Current Methods**:
- `_get_access_token()`: OAuth2 token retrieval
- `enviar_notificacion_push()`: Send notification to token list
- `obtener_tokens_persona()`: Get all tokens for a user
- `notificar_solicitud_aceptada()`: Notify client of accepted request
- `notificar_cambio_estado_servicio()`: Notify client of status change
- `notificar_servicio_finalizado()`: Notify client of completed service

**New Methods to Implement**:

```python
async def notificar_nueva_solicitud_taller(
    db: AsyncSession,
    solicitud: SolicitudServicio,
    id_taller: int
) -> bool:
    """
    Notifies all workshop users when a new service request is created.
    
    Args:
        db: Database session
        solicitud: The new service request
        id_taller: Workshop ID to notify
        
    Returns:
        bool: True if at least one notification was sent successfully
    """
    pass

async def notificar_solicitud_cancelada_taller(
    db: AsyncSession,
    solicitud: SolicitudServicio,
    id_taller: int,
    motivo_cancelacion: str
) -> bool:
    """
    Notifies workshop users when a client cancels a service request.
    
    Args:
        db: Database session
        solicitud: The cancelled service request
        id_taller: Workshop ID to notify
        motivo_cancelacion: Reason for cancellation
        
    Returns:
        bool: True if at least one notification was sent successfully
    """
    pass

async def notificar_diagnostico_completado_taller(
    db: AsyncSession,
    diagnostico: Diagnostico,
    id_taller: int
) -> bool:
    """
    Notifies workshop users when a diagnostic is completed.
    
    Args:
        db: Database session
        diagnostico: The completed diagnostic
        id_taller: Workshop ID to notify
        
    Returns:
        bool: True if at least one notification was sent successfully
    """
    pass

async def notificar_tecnico_asignado(
    db: AsyncSession,
    servicio: Servicio,
    tecnico: Persona
) -> bool:
    """
    Notifies client when a technician is assigned to their service.
    
    Args:
        db: Database session
        servicio: The service with assigned technician
        tecnico: The assigned technician
        
    Returns:
        bool: True if notification was sent successfully
    """
    pass

async def obtener_tokens_usuarios_taller(
    db: AsyncSession,
    id_taller: int
) -> List[str]:
    """
    Gets all device tokens for users associated with a workshop.
    
    Args:
        db: Database session
        id_taller: Workshop ID
        
    Returns:
        List[str]: List of FCM tokens
    """
    pass

async def limpiar_tokens_inactivos(
    db: AsyncSession,
    dias_inactividad: int = 90
) -> int:
    """
    Removes device tokens that have been inactive for specified days.
    
    Args:
        db: Database session
        dias_inactividad: Number of days of inactivity before removal
        
    Returns:
        int: Number of tokens removed
    """
    pass

async def validar_y_limpiar_token(
    db: AsyncSession,
    token: str
) -> bool:
    """
    Validates a token with FCM and removes it if invalid.
    
    Args:
        db: Database session
        token: FCM token to validate
        
    Returns:
        bool: True if token is valid, False if removed
    """
    pass
```

**Enhanced Error Handling**:
- Implement retry logic with exponential backoff (3 attempts)
- Log all notification attempts with structured logging
- Handle FCM-specific error codes (invalid token, quota exceeded, etc.)
- Graceful degradation when FCM is unavailable

#### 2. DispositivoUsuario Model (Enhanced)

**Location**: `P2-backend/app/models/dispositivo_usuario.py`

**Current Schema**:
```python
class DispositivoUsuario(Base):
    __tablename__ = "dispositivo_usuario"
    
    id = Column(Integer, primary_key=True, index=True)
    token_fcm = Column(Text, nullable=False)
    id_persona = Column(Integer, ForeignKey("persona.id", ondelete="CASCADE"))
    
    persona = relationship("Persona", back_populates="dispositivos")
```

**Proposed Enhancements**:
```python
from datetime import datetime
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Boolean

class DispositivoUsuario(Base):
    __tablename__ = "dispositivo_usuario"
    
    id = Column(Integer, primary_key=True, index=True)
    token_fcm = Column(Text, nullable=False, unique=True, index=True)
    id_persona = Column(Integer, ForeignKey("persona.id", ondelete="CASCADE"))
    plataforma = Column(Text, nullable=True)  # 'android', 'ios', 'web'
    activo = Column(Boolean, default=True, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_ultima_actividad = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    persona = relationship("Persona", back_populates="dispositivos")
```

**Migration Required**: Add new columns to existing table.

#### 3. Notification Endpoints (Current)

**Location**: `P2-backend/app/api/api_v1/endpoints/notifications.py`

**Existing Endpoints**:
- `POST /notifications/register-token`: Register FCM token
- `DELETE /notifications/unregister-token`: Unregister FCM token
- `GET /notifications/test-notification`: Send test notification

**No new endpoints required** - notification sending is triggered by system events, not API calls.

### Mobile Components

#### 1. NotificationService (Current Implementation)

**Location**: `P2-mobile/lib/services/notification_service.dart`

**Current Implementation Status**: ✅ Complete

**Key Methods**:
- `initialize()`: Initialize Firebase and request permissions
- `_registerTokenWithBackend()`: Register token with backend
- `unregisterToken()`: Unregister token on logout
- `_setupMessageHandlers()`: Configure message listeners
- `_handleMessage()`: Handle foreground messages
- `_handleMessageTap()`: Handle notification taps
- `firebaseMessagingBackgroundHandler()`: Background message handler

**Required Enhancements**:

```dart
// Add navigation context management
class NotificationService {
  static GlobalKey<NavigatorState>? _navigatorKey;
  
  static void setNavigatorKey(GlobalKey<NavigatorState> key) {
    _navigatorKey = key;
  }
  
  // Enhanced navigation methods with actual routing
  static void _navigateToServiceDetail(String servicioId) {
    if (_navigatorKey?.currentState != null) {
      _navigatorKey!.currentState!.pushNamed(
        '/servicio-detalle',
        arguments: int.parse(servicioId),
      );
    }
  }
  
  static void _navigateToRating(String servicioId) {
    if (_navigatorKey?.currentState != null) {
      _navigatorKey!.currentState!.pushNamed(
        '/valoracion',
        arguments: int.parse(servicioId),
      );
    }
  }
  
  static void _navigateToHome() {
    if (_navigatorKey?.currentState != null) {
      _navigatorKey!.currentState!.pushNamedAndRemoveUntil(
        '/home',
        (route) => false,
      );
    }
  }
  
  // Add foreground notification display
  static void _handleMessage(RemoteMessage message) {
    if (message.notification != null) {
      // Show in-app notification banner
      _showInAppNotification(
        message.notification!.title ?? '',
        message.notification!.body ?? '',
        message.data,
      );
    }
  }
  
  static void _showInAppNotification(
    String title,
    String body,
    Map<String, dynamic> data,
  ) {
    // Use overlay or snackbar to display notification
    if (_navigatorKey?.currentContext != null) {
      ScaffoldMessenger.of(_navigatorKey!.currentContext!).showSnackBar(
        SnackBar(
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(title, style: TextStyle(fontWeight: FontWeight.bold)),
              Text(body),
            ],
          ),
          duration: Duration(seconds: 5),
          action: SnackBarAction(
            label: 'Ver',
            onPressed: () => _handleMessageTap(
              RemoteMessage(data: data, notification: RemoteNotification(title: title, body: body)),
            ),
          ),
        ),
      );
    }
  }
}
```

#### 2. Main App Integration

**Location**: `P2-mobile/lib/main.dart`

**Required Changes**:

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase and notifications
  await NotificationService.initialize();
  
  // Set background message handler
  FirebaseMessaging.onBackgroundMessage(
    NotificationService.firebaseMessagingBackgroundHandler,
  );
  
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
  
  @override
  Widget build(BuildContext context) {
    // Set navigator key for notifications
    NotificationService.setNavigatorKey(navigatorKey);
    
    return MaterialApp(
      navigatorKey: navigatorKey,
      // ... rest of app configuration
    );
  }
}
```

### Web Components

#### 1. Firebase Module

**Location**: `P2-frontend/src/app/core/firebase/firebase.module.ts` (new)

```typescript
import { NgModule } from '@angular/core';
import { initializeApp } from 'firebase/app';
import { getMessaging } from 'firebase/messaging';
import { firebaseConfig } from '../../../firebase.config';

@NgModule({})
export class FirebaseModule {
  constructor() {
    // Initialize Firebase
    const app = initializeApp(firebaseConfig);
    const messaging = getMessaging(app);
  }
}
```

#### 2. NotificationService

**Location**: `P2-frontend/src/app/core/services/notification.service.ts` (new)

```typescript
import { Injectable } from '@angular/core';
import { getMessaging, getToken, onMessage, Messaging } from 'firebase/messaging';
import { BehaviorSubject, Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { vapidKey } from '../../../firebase.config';

export interface NotificationPayload {
  title: string;
  body: string;
  data?: { [key: string]: string };
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private messaging: Messaging;
  private notificationSubject = new BehaviorSubject<NotificationPayload | null>(null);
  public notification$: Observable<NotificationPayload | null> = this.notificationSubject.asObservable();
  
  private permissionStatus: NotificationPermission = 'default';
  private currentToken: string | null = null;

  constructor(private http: HttpClient) {
    this.messaging = getMessaging();
    this.checkPermissionStatus();
  }

  /**
   * Check current notification permission status
   */
  private checkPermissionStatus(): void {
    if ('Notification' in window) {
      this.permissionStatus = Notification.permission;
    }
  }

  /**
   * Request notification permissions and register token
   */
  async requestPermission(): Promise<boolean> {
    try {
      if (!('Notification' in window)) {
        console.warn('This browser does not support notifications');
        return false;
      }

      if (this.permissionStatus === 'granted') {
        await this.registerToken();
        return true;
      }

      const permission = await Notification.requestPermission();
      this.permissionStatus = permission;

      if (permission === 'granted') {
        await this.registerToken();
        return true;
      } else {
        console.log('Notification permission denied');
        return false;
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return false;
    }
  }

  /**
   * Get FCM token and register with backend
   */
  private async registerToken(): Promise<void> {
    try {
      const token = await getToken(this.messaging, { vapidKey });
      
      if (token) {
        console.log('FCM Token obtained:', token.substring(0, 50) + '...');
        this.currentToken = token;
        await this.sendTokenToBackend(token);
        this.setupMessageListener();
      } else {
        console.warn('No FCM token available');
      }
    } catch (error) {
      console.error('Error getting FCM token:', error);
      throw error;
    }
  }

  /**
   * Send token to backend with retry logic
   */
  private async sendTokenToBackend(token: string, retryCount = 0): Promise<void> {
    try {
      const response = await this.http.post(
        `${environment.apiUrl}/notifications/register-token`,
        { token_fcm: token }
      ).toPromise();
      
      console.log('Token registered with backend:', response);
    } catch (error) {
      console.error('Error registering token with backend:', error);
      
      if (retryCount < 3) {
        const delay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        console.log(`Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        await this.sendTokenToBackend(token, retryCount + 1);
      } else {
        throw error;
      }
    }
  }

  /**
   * Setup listener for foreground messages
   */
  private setupMessageListener(): void {
    onMessage(this.messaging, (payload) => {
      console.log('Foreground message received:', payload);
      
      const notification: NotificationPayload = {
        title: payload.notification?.title || 'Notification',
        body: payload.notification?.body || '',
        data: payload.data
      };
      
      this.notificationSubject.next(notification);
      this.playNotificationSound();
    });
  }

  /**
   * Unregister token on logout
   */
  async unregisterToken(): Promise<void> {
    if (!this.currentToken) return;

    try {
      await this.http.delete(
        `${environment.apiUrl}/notifications/unregister-token`,
        { body: { token_fcm: this.currentToken } }
      ).toPromise();
      
      console.log('Token unregistered from backend');
      this.currentToken = null;
    } catch (error) {
      console.error('Error unregistering token:', error);
    }
  }

  /**
   * Play notification sound
   */
  private playNotificationSound(): void {
    const audio = new Audio('/assets/sounds/notification.mp3');
    audio.play().catch(err => console.warn('Could not play notification sound:', err));
  }

  /**
   * Get current permission status
   */
  getPermissionStatus(): NotificationPermission {
    return this.permissionStatus;
  }

  /**
   * Manually refresh FCM token
   */
  async refreshToken(): Promise<void> {
    await this.registerToken();
  }
}
```

#### 3. Service Worker

**Location**: `P2-frontend/public/firebase-messaging-sw.js` (new)

```javascript
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// Initialize Firebase in Service Worker
firebase.initializeApp({
  apiKey: "AIzaSyAvdpjx1YccTHqji2XpwZJX2THnoaXmcOg",
  authDomain: "asistencia-vehicular-890e2.firebaseapp.com",
  projectId: "asistencia-vehicular-890e2",
  storageBucket: "asistencia-vehicular-890e2.firebasestorage.app",
  messagingSenderId: "770812655534",
  appId: "1:770812655534:web:66a5392e14282547623a3f"
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log('Background message received:', payload);

  const notificationTitle = payload.notification?.title || 'Notification';
  const notificationOptions = {
    body: payload.notification?.body || '',
    icon: '/assets/icons/icon-192x192.png',
    badge: '/assets/icons/badge-72x72.png',
    data: payload.data,
    tag: payload.data?.tipo || 'default',
    requireInteraction: true
  };

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event.notification);
  
  event.notification.close();

  const data = event.notification.data;
  const accion = data?.accion;
  
  let urlToOpen = '/';
  
  switch (accion) {
    case 'abrir_solicitud_detalle':
      urlToOpen = `/solicitudes/${data.solicitud_id}`;
      break;
    case 'abrir_diagnostico_detalle':
      urlToOpen = `/diagnosticos/${data.diagnostico_id}`;
      break;
    case 'abrir_solicitudes_lista':
      urlToOpen = '/solicitudes';
      break;
    default:
      urlToOpen = '/dashboard';
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Check if there's already a window open
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.postMessage({
              type: 'NOTIFICATION_CLICK',
              url: urlToOpen,
              data: data
            });
            return client.focus();
          }
        }
        // If no window is open, open a new one
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});
```

#### 4. Notification Toast Component

**Location**: `P2-frontend/src/app/shared/components/notification-toast/notification-toast.component.ts` (new)

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { NotificationService, NotificationPayload } from '../../../core/services/notification.service';

@Component({
  selector: 'app-notification-toast',
  template: `
    <div class="notification-container">
      <div *ngFor="let notification of notifications" 
           class="notification-toast"
           [@slideIn]>
        <div class="notification-icon">
          <i class="fas fa-bell"></i>
        </div>
        <div class="notification-content">
          <h4>{{ notification.title }}</h4>
          <p>{{ notification.body }}</p>
        </div>
        <div class="notification-actions">
          <button (click)="handleNotificationClick(notification)" class="btn-view">
            Ver
          </button>
          <button (click)="dismissNotification(notification)" class="btn-dismiss">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .notification-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 400px;
    }
    
    .notification-toast {
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      padding: 16px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      animation: slideIn 0.3s ease-out;
    }
    
    .notification-icon {
      font-size: 24px;
      color: #2196F3;
    }
    
    .notification-content {
      flex: 1;
    }
    
    .notification-content h4 {
      margin: 0 0 4px 0;
      font-size: 16px;
      font-weight: 600;
    }
    
    .notification-content p {
      margin: 0;
      font-size: 14px;
      color: #666;
    }
    
    .notification-actions {
      display: flex;
      gap: 8px;
    }
    
    .btn-view, .btn-dismiss {
      padding: 6px 12px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }
    
    .btn-view {
      background: #2196F3;
      color: white;
    }
    
    .btn-dismiss {
      background: #f5f5f5;
      color: #666;
    }
    
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
  `]
})
export class NotificationToastComponent implements OnInit, OnDestroy {
  notifications: NotificationPayload[] = [];
  private subscription?: Subscription;

  constructor(
    private notificationService: NotificationService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.subscription = this.notificationService.notification$.subscribe(
      (notification) => {
        if (notification) {
          this.notifications.push(notification);
          
          // Auto-dismiss after 8 seconds
          setTimeout(() => {
            this.dismissNotification(notification);
          }, 8000);
        }
      }
    );
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  handleNotificationClick(notification: NotificationPayload): void {
    const accion = notification.data?.['accion'];
    
    switch (accion) {
      case 'abrir_solicitud_detalle':
        this.router.navigate(['/solicitudes', notification.data?.['solicitud_id']]);
        break;
      case 'abrir_diagnostico_detalle':
        this.router.navigate(['/diagnosticos', notification.data?.['diagnostico_id']]);
        break;
      case 'abrir_solicitudes_lista':
        this.router.navigate(['/solicitudes']);
        break;
      default:
        this.router.navigate(['/dashboard']);
    }
    
    this.dismissNotification(notification);
  }

  dismissNotification(notification: NotificationPayload): void {
    const index = this.notifications.indexOf(notification);
    if (index > -1) {
      this.notifications.splice(index, 1);
    }
  }
}
```

#### 5. App Component Integration

**Location**: `P2-frontend/src/app/app.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { NotificationService } from './core/services/notification.service';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  template: `
    <router-outlet></router-outlet>
    <app-notification-toast></app-notification-toast>
  `
})
export class AppComponent implements OnInit {
  constructor(
    private notificationService: NotificationService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    // Request notification permissions after user logs in
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.notificationService.requestPermission();
      }
    });
    
    // Listen for Service Worker messages
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data.type === 'NOTIFICATION_CLICK') {
          // Handle navigation from Service Worker
          window.location.href = event.data.url;
        }
      });
    }
  }
}
```



## Data Models

### Notification Payload Structure

All notifications sent through FCM follow a consistent structure:

```json
{
  "message": {
    "token": "device_fcm_token_here",
    "notification": {
      "title": "Notification Title",
      "body": "Notification message body"
    },
    "data": {
      "tipo": "notification_type",
      "accion": "action_to_perform",
      "servicio_id": "123",
      "solicitud_id": "456",
      "diagnostico_id": "789",
      "tecnico_id": "101",
      "timestamp": "1234567890"
    },
    "android": {
      "priority": "high",
      "notification": {
        "sound": "default",
        "channel_id": "default"
      }
    },
    "webpush": {
      "headers": {
        "Urgency": "high"
      },
      "notification": {
        "icon": "/assets/icons/icon-192x192.png",
        "badge": "/assets/icons/badge-72x72.png"
      }
    }
  }
}
```

### Notification Types and Actions

| Notification Type | Target User | Action | Description |
|------------------|-------------|--------|-------------|
| `nueva_solicitud` | Workshop | `abrir_solicitud_detalle` | New service request created |
| `solicitud_cancelada` | Workshop | `abrir_solicitudes_lista` | Client cancelled service request |
| `diagnostico_completado` | Workshop | `abrir_diagnostico_detalle` | Technician completed diagnostic |
| `solicitud_aceptada` | Client | `abrir_servicio_detalle` | Workshop accepted service request |
| `tecnico_asignado` | Client | `abrir_servicio_detalle` | Technician assigned to service |
| `tecnico_en_camino` | Client | `abrir_servicio_detalle` | Technician is on the way |
| `tecnico_en_lugar` | Client | `abrir_servicio_detalle` | Technician arrived at location |
| `servicio_en_atencion` | Client | `abrir_servicio_detalle` | Service is in progress |
| `servicio_finalizado` | Client | `abrir_valoracion` | Service completed, prompt for rating |
| `servicio_cancelado` | Client | `abrir_solicitudes_lista` | Workshop cancelled service |

### Database Schema

#### DispositivoUsuario Table (Enhanced)

```sql
CREATE TABLE dispositivo_usuario (
    id SERIAL PRIMARY KEY,
    token_fcm TEXT NOT NULL UNIQUE,
    id_persona INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    plataforma VARCHAR(20),  -- 'android', 'ios', 'web'
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_ultima_actividad TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_token_fcm (token_fcm),
    INDEX idx_id_persona (id_persona),
    INDEX idx_activo (activo)
);
```

**Migration Script**:
```sql
-- Add new columns to existing table
ALTER TABLE dispositivo_usuario 
ADD COLUMN plataforma VARCHAR(20),
ADD COLUMN activo BOOLEAN NOT NULL DEFAULT TRUE,
ADD COLUMN fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
ADD COLUMN fecha_ultima_actividad TIMESTAMP NOT NULL DEFAULT NOW();

-- Add unique constraint to token_fcm if not exists
ALTER TABLE dispositivo_usuario 
ADD CONSTRAINT dispositivo_usuario_token_fcm_key UNIQUE (token_fcm);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dispositivo_usuario_token_fcm ON dispositivo_usuario(token_fcm);
CREATE INDEX IF NOT EXISTS idx_dispositivo_usuario_id_persona ON dispositivo_usuario(id_persona);
CREATE INDEX IF NOT EXISTS idx_dispositivo_usuario_activo ON dispositivo_usuario(activo);
```

### Notification Preferences (Future Enhancement)

For Requirement 29, a new table will be needed:

```sql
CREATE TABLE preferencias_notificacion (
    id SERIAL PRIMARY KEY,
    id_persona INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    tipo_notificacion VARCHAR(50) NOT NULL,
    habilitado BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(id_persona, tipo_notificacion),
    INDEX idx_id_persona (id_persona)
);
```

## API Contracts

### Existing Endpoints

#### POST /api/v1/notifications/register-token

**Description**: Register or update FCM device token for the authenticated user.

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "token_fcm": "string (FCM device token)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Token FCM registrado exitosamente"
}
```

**Error Responses**:
- 401 Unauthorized: Invalid or missing authentication token
- 500 Internal Server Error: Database or server error

**Behavior**:
- If token exists for a different user, reassigns it to current user
- If token exists for current user, returns success without changes
- If token doesn't exist, creates new DispositivoUsuario record
- Updates `fecha_ultima_actividad` on each registration

#### DELETE /api/v1/notifications/unregister-token

**Description**: Remove FCM device token (called on logout).

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "token_fcm": "string (FCM device token)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Token FCM eliminado exitosamente"
}
```

**Behavior**:
- Marks token as inactive (`activo = false`) rather than deleting
- Only processes if token belongs to authenticated user
- Returns success even if token not found (idempotent)

#### GET /api/v1/notifications/test-notification

**Description**: Send a test notification to the authenticated user's devices.

**Authentication**: Required (Bearer token)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Notificación enviada",
  "tokens_count": 2
}
```

**Response** (200 OK - No tokens):
```json
{
  "success": false,
  "message": "No hay tokens FCM registrados"
}
```

### Internal Notification Triggers

Notifications are triggered by system events, not direct API calls. The following events trigger notifications:

#### Workshop Notifications

1. **New Service Request Created**
   - Event: `SolicitudServicio` created
   - Trigger: `notificar_nueva_solicitud_taller()`
   - Recipients: All users associated with target workshop

2. **Service Request Cancelled by Client**
   - Event: `SolicitudServicio.estado` changed to "cancelado"
   - Trigger: `notificar_solicitud_cancelada_taller()`
   - Recipients: All users associated with workshop

3. **Diagnostic Completed**
   - Event: `Diagnostico.estado` changed to "completado"
   - Trigger: `notificar_diagnostico_completado_taller()`
   - Recipients: All users associated with workshop

#### Client Notifications

1. **Service Request Accepted**
   - Event: Workshop accepts `SolicitudServicio`
   - Trigger: `notificar_solicitud_aceptada()`
   - Recipients: Client who created the request

2. **Technician Assigned**
   - Event: `Servicio.id_tecnico` assigned
   - Trigger: `notificar_tecnico_asignado()`
   - Recipients: Client associated with service

3. **Status Changes**
   - Event: `Servicio.estado` changes
   - Trigger: `notificar_cambio_estado_servicio()`
   - Recipients: Client associated with service
   - States: "en_camino", "en_lugar", "en_atencion"

4. **Service Completed**
   - Event: `Servicio.estado` changed to "finalizado"
   - Trigger: `notificar_servicio_finalizado()`
   - Recipients: Client associated with service

5. **Service Cancelled by Workshop**
   - Event: `Servicio.estado` changed to "cancelado" by workshop
   - Trigger: `notificar_cambio_estado_servicio()`
   - Recipients: Client associated with service

## Error Handling

### Backend Error Handling Strategy

#### FCM API Errors

```python
class FCMErrorHandler:
    """Handles FCM-specific errors with appropriate actions"""
    
    @staticmethod
    async def handle_fcm_error(
        error_code: int,
        error_message: str,
        token: str,
        db: AsyncSession
    ) -> None:
        """
        Handle FCM API errors based on status code
        
        Args:
            error_code: HTTP status code from FCM
            error_message: Error message from FCM
            token: The FCM token that caused the error
            db: Database session
        """
        if error_code == 404:
            # Token not found - remove from database
            logger.warning(f"Token not found in FCM, removing: {token[:20]}...")
            await crud_dispositivo_usuario.dispositivo_usuario.delete_by_token(db, token)
            
        elif error_code == 400:
            # Invalid token format - remove from database
            logger.error(f"Invalid token format, removing: {token[:20]}...")
            await crud_dispositivo_usuario.dispositivo_usuario.delete_by_token(db, token)
            
        elif error_code == 401:
            # Authentication error - refresh OAuth token
            logger.error("FCM authentication failed, refreshing token...")
            # Token will be refreshed on next attempt
            
        elif error_code == 429:
            # Rate limit exceeded - log and continue
            logger.warning("FCM rate limit exceeded, will retry later")
            
        elif error_code >= 500:
            # Server error - retry with backoff
            logger.error(f"FCM server error {error_code}: {error_message}")
            # Handled by retry logic
            
        else:
            # Unknown error - log for investigation
            logger.error(f"Unknown FCM error {error_code}: {error_message}")
```

#### Retry Logic with Exponential Backoff

```python
async def enviar_notificacion_con_reintentos(
    tokens: List[str],
    titulo: str,
    mensaje: str,
    datos_extra: Optional[Dict[str, Any]] = None,
    max_intentos: int = 3
) -> bool:
    """
    Send notification with retry logic
    
    Args:
        tokens: List of FCM tokens
        titulo: Notification title
        mensaje: Notification message
        datos_extra: Additional data payload
        max_intentos: Maximum number of retry attempts
        
    Returns:
        bool: True if at least one notification was sent successfully
    """
    for intento in range(max_intentos):
        try:
            success = await notification_service.enviar_notificacion_push(
                tokens, titulo, mensaje, datos_extra
            )
            
            if success:
                return True
                
        except httpx.TimeoutException:
            if intento < max_intentos - 1:
                delay = (2 ** intento) * 1000  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Timeout, retrying in {delay}ms... (attempt {intento + 1}/{max_intentos})")
                await asyncio.sleep(delay / 1000)
            else:
                logger.error("Max retry attempts reached, notification failed")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            if intento < max_intentos - 1:
                delay = (2 ** intento) * 1000
                await asyncio.sleep(delay / 1000)
            else:
                return False
    
    return False
```

#### Graceful Degradation

```python
async def notificar_con_fallback(
    db: AsyncSession,
    id_persona: int,
    titulo: str,
    mensaje: str,
    datos_extra: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send notification with graceful degradation
    
    If FCM is unavailable, the system continues operation without throwing exceptions.
    Notifications are logged for later retry or manual follow-up.
    
    Args:
        db: Database session
        id_persona: User ID to notify
        titulo: Notification title
        mensaje: Notification message
        datos_extra: Additional data payload
        
    Returns:
        bool: True if notification was sent, False if failed gracefully
    """
    try:
        tokens = await notification_service.obtener_tokens_persona(db, id_persona)
        
        if not tokens:
            logger.info(f"No tokens found for user {id_persona}, skipping notification")
            return True  # Not an error, just no devices registered
        
        success = await enviar_notificacion_con_reintentos(
            tokens, titulo, mensaje, datos_extra
        )
        
        if not success:
            logger.warning(
                f"Failed to send notification to user {id_persona}: {titulo}",
                extra={
                    "user_id": id_persona,
                    "notification_title": titulo,
                    "notification_body": mensaje,
                    "data": datos_extra
                }
            )
        
        return success
        
    except Exception as e:
        # Log error but don't raise - system continues operation
        logger.error(
            f"Error in notification system for user {id_persona}: {e}",
            exc_info=True,
            extra={
                "user_id": id_persona,
                "notification_title": titulo
            }
        )
        return False
```

### Mobile Error Handling

#### Permission Denied

```dart
static Future<void> initialize() async {
  try {
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      print('❌ Notification permissions denied by user');
      // Store denial in local storage to avoid repeated requests
      await _storePermissionDenial();
      return;
    }
    
    if (settings.authorizationStatus == AuthorizationStatus.notDetermined) {
      print('⚠️ Notification permissions not determined');
      return;
    }
    
    // Continue with token registration...
    
  } catch (e) {
    print('💥 Error requesting permissions: $e');
    // Continue app operation without notifications
  }
}
```

#### Token Registration Failure

```dart
static Future<void> _registerTokenWithBackend(String token) async {
  int maxRetries = 3;
  int retryCount = 0;
  
  while (retryCount < maxRetries) {
    try {
      final sessionToken = await Session.getToken();
      if (sessionToken == null) {
        print('❌ No active session, cannot register token');
        return;
      }

      final response = await http.post(
        Uri.parse('$baseUrl/notifications/register-token'),
        headers: {
          'Authorization': 'Bearer $sessionToken',
          'Content-Type': 'application/json',
        },
        body: json.encode({'token_fcm': token}),
      ).timeout(Duration(seconds: 10));

      if (response.statusCode == 200) {
        print('✅ Token registered successfully');
        return;
      } else {
        print('❌ Error registering token: ${response.statusCode}');
        retryCount++;
      }
      
    } on TimeoutException {
      print('⏱️ Token registration timeout, retrying...');
      retryCount++;
      await Future.delayed(Duration(seconds: 2 * retryCount));
      
    } catch (e) {
      print('💥 Error registering token: $e');
      retryCount++;
      await Future.delayed(Duration(seconds: 2 * retryCount));
    }
  }
  
  print('❌ Failed to register token after $maxRetries attempts');
}
```

#### Network Connectivity

```dart
static Future<bool> _checkConnectivity() async {
  try {
    final result = await InternetAddress.lookup('google.com');
    return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
  } catch (e) {
    return false;
  }
}

static Future<void> _registerTokenWithBackend(String token) async {
  if (!await _checkConnectivity()) {
    print('❌ No internet connection, will retry when online');
    // Schedule retry when connectivity is restored
    _scheduleTokenRegistrationRetry(token);
    return;
  }
  
  // Continue with registration...
}
```

### Web Error Handling

#### Browser Compatibility

```typescript
async requestPermission(): Promise<boolean> {
  try {
    // Check browser support
    if (!('Notification' in window)) {
      console.warn('This browser does not support notifications');
      this.showBrowserNotSupportedMessage();
      return false;
    }
    
    if (!('serviceWorker' in navigator)) {
      console.warn('This browser does not support Service Workers');
      this.showBrowserNotSupportedMessage();
      return false;
    }
    
    // Check if running in secure context (HTTPS)
    if (!window.isSecureContext) {
      console.error('Notifications require HTTPS');
      this.showSecureContextRequiredMessage();
      return false;
    }
    
    // Continue with permission request...
    
  } catch (error) {
    console.error('Error requesting notification permission:', error);
    return false;
  }
}

private showBrowserNotSupportedMessage(): void {
  // Show user-friendly message about browser compatibility
  this.toastr.warning(
    'Your browser does not support push notifications. Please use a modern browser like Chrome, Firefox, or Edge.',
    'Notifications Not Supported'
  );
}
```

#### Service Worker Registration Failure

```typescript
async registerServiceWorker(): Promise<void> {
  try {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.register(
        '/firebase-messaging-sw.js',
        { scope: '/' }
      );
      
      console.log('Service Worker registered:', registration);
      
      // Wait for Service Worker to be ready
      await navigator.serviceWorker.ready;
      console.log('Service Worker is ready');
      
    }
  } catch (error) {
    console.error('Service Worker registration failed:', error);
    
    // Fallback: Use foreground notifications only
    this.useForegroundOnlyMode();
  }
}

private useForegroundOnlyMode(): void {
  console.log('Using foreground-only notification mode');
  // Only show notifications when app is active
  // Background notifications will not work
}
```

#### Token Refresh Failure

```typescript
private async registerToken(): Promise<void> {
  try {
    const token = await getToken(this.messaging, { vapidKey });
    
    if (token) {
      this.currentToken = token;
      await this.sendTokenToBackend(token);
    } else {
      console.warn('No FCM token available');
      
      // Retry after delay
      setTimeout(() => {
        this.registerToken();
      }, 5000);
    }
  } catch (error) {
    if (error.code === 'messaging/permission-blocked') {
      console.error('Notification permissions are blocked');
      this.showPermissionBlockedMessage();
    } else if (error.code === 'messaging/token-subscribe-failed') {
      console.error('Failed to subscribe to FCM');
      // Retry with exponential backoff
      this.retryTokenRegistration();
    } else {
      console.error('Error getting FCM token:', error);
    }
  }
}
```

### Logging and Monitoring

#### Structured Logging

```python
import logging
import json
from datetime import datetime

class NotificationLogger:
    """Structured logging for notification events"""
    
    @staticmethod
    def log_notification_sent(
        user_id: int,
        notification_type: str,
        tokens_count: int,
        success_count: int,
        failure_count: int
    ):
        logger.info(
            "Notification sent",
            extra={
                "event": "notification_sent",
                "user_id": user_id,
                "notification_type": notification_type,
                "tokens_count": tokens_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_notification_failed(
        user_id: int,
        notification_type: str,
        error_message: str,
        error_code: Optional[int] = None
    ):
        logger.error(
            "Notification failed",
            extra={
                "event": "notification_failed",
                "user_id": user_id,
                "notification_type": notification_type,
                "error_message": error_message,
                "error_code": error_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_token_registered(user_id: int, platform: str):
        logger.info(
            "Token registered",
            extra={
                "event": "token_registered",
                "user_id": user_id,
                "platform": platform,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_token_removed(user_id: int, reason: str):
        logger.info(
            "Token removed",
            extra={
                "event": "token_removed",
                "user_id": user_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

#### Health Check Endpoint

```python
@router.get("/notifications/health")
async def notification_health_check():
    """
    Health check endpoint for notification system
    """
    try:
        # Check FCM credentials
        fcm_configured = notification_service.fcm_credentials_path is not None
        
        # Try to get access token
        access_token = notification_service._get_access_token()
        fcm_accessible = access_token is not None
        
        # Check database connectivity
        async with get_db() as db:
            result = await db.execute(select(DispositivoUsuario).limit(1))
            db_accessible = True
        
        status = "healthy" if (fcm_configured and fcm_accessible and db_accessible) else "degraded"
        
        return {
            "status": status,
            "fcm_configured": fcm_configured,
            "fcm_accessible": fcm_accessible,
            "database_accessible": db_accessible,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```



## Integration Points

### Backend Integration Points

The following endpoints and service methods need to trigger notifications:

#### 1. Service Request Creation
**File**: `P2-backend/app/services/solicitud_servicio_service.py`
**Method**: `crear_solicitudes_servicio_automaticas()` and `crear_solicitud_servicio_manual()`

```python
# After creating SolicitudServicio
await notification_service.notificar_nueva_solicitud_taller(
    db=db,
    solicitud=nueva_solicitud,
    id_taller=nueva_solicitud.id_taller
)
```

#### 2. Service Request Cancellation
**File**: `P2-backend/app/api/api_v1/endpoints/servicios.py`
**Endpoint**: `DELETE /servicios/{solicitud_id}`

```python
# After updating estado to cancelada
await notification_service.notificar_solicitud_cancelada_taller(
    db=db,
    solicitud=solicitud,
    id_taller=solicitud.id_taller,
    motivo_cancelacion="Cancelado por el cliente"
)
```

#### 3. Service Request Acceptance (Workshop accepts)
**File**: `P2-backend/app/api/api_v1/endpoints/taller_servicios.py`
**Method**: When workshop accepts a solicitud and creates Servicio

```python
# After creating Servicio from accepted SolicitudServicio
await notification_service.notificar_solicitud_aceptada(
    db=db,
    servicio=nuevo_servicio
)
```

#### 4. Technician Assignment
**File**: `P2-backend/app/api/api_v1/endpoints/taller_servicios.py` or `tecnico_servicios.py`
**Method**: When assigning technician to service

```python
# After assigning technician
await notification_service.notificar_tecnico_asignado(
    db=db,
    servicio=servicio,
    tecnico=tecnico_persona
)
```

#### 5. Service Status Changes
**File**: `P2-backend/app/api/api_v1/endpoints/tecnico_servicios.py`
**Method**: When technician updates service status

```python
# After updating Servicio.estado
if nuevo_estado in [EstadoServicio.en_camino, EstadoServicio.en_lugar, EstadoServicio.en_atencion]:
    await notification_service.notificar_cambio_estado_servicio(
        db=db,
        servicio=servicio,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado
    )
```

#### 6. Service Completion
**File**: `P2-backend/app/api/api_v1/endpoints/tecnico_servicios.py`
**Method**: When service is marked as finalizado

```python
# After updating estado to finalizado
await notification_service.notificar_servicio_finalizado(
    db=db,
    servicio=servicio
)
```

#### 7. Diagnostic Completion
**File**: `P2-backend/app/api/api_v1/endpoints/diagnosticos.py`
**Method**: When diagnostic is completed

```python
# After marking diagnostic as completed
await notification_service.notificar_diagnostico_completado_taller(
    db=db,
    diagnostico=diagnostico,
    id_taller=servicio.id_taller
)
```

### Mobile Integration Points

#### 1. Login Flow
**File**: `P2-mobile/lib/screens/auth/login_screen.dart`

```dart
// After successful login
await NotificationService.initialize();
```

#### 2. Logout Flow
**File**: `P2-mobile/lib/services/auth_service.dart`

```dart
// Before clearing session
await NotificationService.unregisterToken();
```

#### 3. Navigation Setup
**File**: `P2-mobile/lib/main.dart`

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.initialize();
  
  FirebaseMessaging.onBackgroundMessage(
    NotificationService.firebaseMessagingBackgroundHandler
  );
  
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
  
  @override
  Widget build(BuildContext context) {
    NotificationService.setNavigatorKey(navigatorKey);
    
    return MaterialApp(
      navigatorKey: navigatorKey,
      routes: {
        '/servicio-detalle': (context) => ServicioDetalleScreen(),
        '/valoracion': (context) => ValoracionScreen(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}
```

### Web Integration Points

#### 1. App Module
**File**: `P2-frontend/src/app/app.module.ts`

```typescript
import { FirebaseModule } from './core/firebase/firebase.module';
import { NotificationService } from './core/services/notification.service';

@NgModule({
  imports: [
    // ... other imports
    FirebaseModule
  ],
  providers: [
    NotificationService,
    // ... other providers
  ]
})
export class AppModule { }
```

#### 2. Login Component
**File**: `P2-frontend/src/app/features/auth/login/login.component.ts`

```typescript
async onLoginSuccess() {
  // After successful login
  await this.notificationService.requestPermission();
  this.router.navigate(['/dashboard']);
}
```

#### 3. Logout Component
**File**: `P2-frontend/src/app/core/services/auth.service.ts`

```typescript
async logout() {
  await this.notificationService.unregisterToken();
  // Clear session and redirect to login
}
```

#### 4. Service Worker Registration
**File**: `P2-frontend/src/main.ts`

```typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .then(() => {
    // Register Service Worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/firebase-messaging-sw.js')
        .then(registration => {
          console.log('Service Worker registered:', registration);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });
    }
  })
  .catch(err => console.error(err));
```

#### 5. App Component
**File**: `P2-frontend/src/app/app.component.ts`

```typescript
export class AppComponent implements OnInit {
  constructor(
    private notificationService: NotificationService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Request permissions after login
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.notificationService.requestPermission();
      }
    });
    
    // Handle Service Worker messages
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data.type === 'NOTIFICATION_CLICK') {
          this.router.navigateByUrl(event.data.url);
        }
      });
    }
  }
}
```

## Testing Strategy

### Unit Tests

#### Backend Unit Tests

**File**: `P2-backend/tests/services/test_notification_service.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_enviar_notificacion_push_success():
    """Test successful notification sending"""
    service = NotificationService()
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.status_code = 200
        
        result = await service.enviar_notificacion_push(
            tokens=['test_token'],
            titulo='Test',
            mensaje='Test message'
        )
        
        assert result is True
        assert mock_post.called

@pytest.mark.asyncio
async def test_enviar_notificacion_push_invalid_token():
    """Test handling of invalid token"""
    service = NotificationService()
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.status_code = 404
        
        result = await service.enviar_notificacion_push(
            tokens=['invalid_token'],
            titulo='Test',
            mensaje='Test message'
        )
        
        # Should log error but not raise exception
        assert result is False

@pytest.mark.asyncio
async def test_obtener_tokens_persona():
    """Test retrieving user tokens"""
    service = NotificationService()
    mock_db = AsyncMock()
    
    with patch('app.crud.crud_dispositivo_usuario.dispositivo_usuario.get_by_persona') as mock_get:
        mock_get.return_value = [
            Mock(token_fcm='token1'),
            Mock(token_fcm='token2')
        ]
        
        tokens = await service.obtener_tokens_persona(mock_db, 123)
        
        assert len(tokens) == 2
        assert 'token1' in tokens
        assert 'token2' in tokens

@pytest.mark.asyncio
async def test_notificar_solicitud_aceptada():
    """Test client notification for accepted request"""
    service = NotificationService()
    mock_db = AsyncMock()
    mock_servicio = Mock(id=1, id_solicitud_servicio=1)
    
    with patch.object(service, 'obtener_tokens_persona', return_value=['token1']):
        with patch.object(service, 'enviar_notificacion_push', return_value=True):
            result = await service.notificar_solicitud_aceptada(mock_db, mock_servicio)
            
            assert result is True
```

#### Mobile Unit Tests

**File**: `P2-mobile/test/services/notification_service_test.dart`

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:mobile_repo/services/notification_service.dart';

void main() {
  group('NotificationService', () {
    test('initialize requests permissions', () async {
      // Mock Firebase Messaging
      final mockMessaging = MockFirebaseMessaging();
      
      when(mockMessaging.requestPermission()).thenAnswer(
        (_) async => NotificationSettings(
          authorizationStatus: AuthorizationStatus.authorized,
        ),
      );
      
      await NotificationService.initialize();
      
      verify(mockMessaging.requestPermission()).called(1);
    });
    
    test('handleMessageTap navigates to correct screen', () {
      final message = RemoteMessage(
        data: {
          'accion': 'abrir_servicio_detalle',
          'servicio_id': '123',
        },
      );
      
      // Mock navigator
      final mockNavigator = MockNavigatorState();
      NotificationService.setNavigatorKey(GlobalKey<NavigatorState>());
      
      NotificationService._handleMessageTap(message);
      
      // Verify navigation was called
      // (requires more complex mocking setup)
    });
  });
}
```

#### Web Unit Tests

**File**: `P2-frontend/src/app/core/services/notification.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { NotificationService } from './notification.service';

describe('NotificationService', () => {
  let service: NotificationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [NotificationService]
    });
    
    service = TestBed.inject(NotificationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should send token to backend', async () => {
    const mockToken = 'test_fcm_token';
    
    service['sendTokenToBackend'](mockToken);
    
    const req = httpMock.expectOne(`${environment.apiUrl}/notifications/register-token`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ token_fcm: mockToken });
    
    req.flush({ success: true, message: 'Token registered' });
  });

  it('should retry on failure', async () => {
    const mockToken = 'test_fcm_token';
    
    service['sendTokenToBackend'](mockToken);
    
    // First attempt fails
    const req1 = httpMock.expectOne(`${environment.apiUrl}/notifications/register-token`);
    req1.flush({ error: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });
    
    // Should retry
    const req2 = httpMock.expectOne(`${environment.apiUrl}/notifications/register-token`);
    req2.flush({ success: true, message: 'Token registered' });
  });
});
```

### Integration Tests

#### Backend Integration Tests

**File**: `P2-backend/tests/integration/test_notifications_flow.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_token_flow(async_client: AsyncClient, auth_headers):
    """Test complete token registration flow"""
    
    # Register token
    response = await async_client.post(
        "/api/v1/notifications/register-token",
        headers=auth_headers,
        json={"token_fcm": "test_token_123"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify token is stored
    # (requires database query)

@pytest.mark.asyncio
async def test_notification_on_service_creation(async_client: AsyncClient, auth_headers):
    """Test that notification is sent when service is created"""
    
    # Create service request
    response = await async_client.post(
        "/api/v1/servicios/1/solicitar-taller",
        headers=auth_headers,
        data={"id_taller": 1}
    )
    
    assert response.status_code == 201
    
    # Verify notification was sent
    # (requires mocking FCM or checking logs)
```

#### End-to-End Tests

**File**: `P2-backend/tests/e2e/test_notification_delivery.py`

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_notification_flow():
    """
    Test complete notification flow from trigger to delivery
    
    1. Client creates service request
    2. Backend sends notification to workshop
    3. Workshop receives notification
    4. Workshop accepts request
    5. Backend sends notification to client
    6. Client receives notification
    """
    
    # This test requires:
    # - Real Firebase project
    # - Test devices with registered tokens
    # - Ability to verify notification receipt
    
    pass  # Implementation depends on test infrastructure
```

### Manual Testing Checklist

#### Backend Testing

- [ ] Register FCM token via API
- [ ] Unregister FCM token via API
- [ ] Send test notification via `/notifications/test-notification`
- [ ] Verify notification appears on device
- [ ] Test with multiple devices per user
- [ ] Test token reassignment (same token, different user)
- [ ] Test invalid token handling
- [ ] Test FCM API unavailability
- [ ] Verify logging for all notification events
- [ ] Test notification for each workflow event (20+ scenarios)

#### Mobile Testing

- [ ] Request notification permissions on first launch
- [ ] Register token after login
- [ ] Receive foreground notification (app open)
- [ ] Receive background notification (app minimized)
- [ ] Receive notification when app is terminated
- [ ] Tap notification and verify navigation
- [ ] Test notification with different action types
- [ ] Verify token refresh on Firebase token change
- [ ] Unregister token on logout
- [ ] Test on Android device
- [ ] Test on iOS device (if applicable)
- [ ] Test with poor network connectivity
- [ ] Test permission denial handling

#### Web Testing

- [ ] Request notification permissions on login
- [ ] Register token after permission granted
- [ ] Receive foreground notification (tab active)
- [ ] Receive background notification (tab inactive)
- [ ] Receive notification when browser is closed
- [ ] Click notification and verify navigation
- [ ] Test notification toast display
- [ ] Test notification sound playback
- [ ] Verify Service Worker registration
- [ ] Test on Chrome browser
- [ ] Test on Firefox browser
- [ ] Test on Edge browser
- [ ] Test on Safari browser (if applicable)
- [ ] Test with browser notifications blocked
- [ ] Test with Service Worker disabled
- [ ] Unregister token on logout

### Performance Testing

#### Load Testing

```python
# Test notification sending to 1000 users
@pytest.mark.performance
async def test_bulk_notification_performance():
    """Test sending notifications to many users"""
    
    start_time = time.time()
    
    # Send notification to 1000 users
    tasks = []
    for user_id in range(1, 1001):
        task = notification_service.notificar_con_fallback(
            db, user_id, "Test", "Performance test"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Sent {len(results)} notifications in {duration:.2f} seconds")
    print(f"Average: {duration/len(results):.3f} seconds per notification")
    
    assert duration < 60  # Should complete within 1 minute
```

#### Token Cleanup Performance

```python
@pytest.mark.performance
async def test_token_cleanup_performance():
    """Test performance of inactive token cleanup"""
    
    # Create 10,000 inactive tokens
    # Run cleanup
    # Measure time
    
    start_time = time.time()
    removed_count = await notification_service.limpiar_tokens_inactivos(db, dias=90)
    end_time = time.time()
    
    print(f"Removed {removed_count} tokens in {end_time - start_time:.2f} seconds")
```

## Deployment Considerations

### Backend Deployment

#### Environment Variables

Ensure the following environment variables are set:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=asistencia-vehicular-890e2
FCM_CREDENTIALS_PATH=firebase-credentials.json
FCM_VAPID_KEY=BOO39zp0Vpsd10Muf2nntKKpdmegxhs13PuZAMVAgJfrGXDnZdgecRIL2SnqpzAcolXGCWzO9J8xHOafTJwPPmY
```

#### Database Migration

Run the migration to add new columns to `dispositivo_usuario`:

```bash
# Generate migration
alembic revision --autogenerate -m "Add notification tracking fields to dispositivo_usuario"

# Review migration file
# Edit if necessary

# Apply migration
alembic upgrade head
```

#### Firebase Credentials

Ensure `firebase-credentials.json` is:
- Present in the deployment environment
- Has correct permissions (readable by application)
- Is NOT committed to version control
- Is included in `.gitignore`

### Mobile Deployment

#### Android Configuration

1. Ensure `google-services.json` is in `android/app/`
2. Verify Google Services plugin in `android/app/build.gradle.kts`
3. Test on physical device (emulator may have issues with FCM)

#### iOS Configuration (if applicable)

1. Add `GoogleService-Info.plist` to iOS project
2. Configure APNs certificates in Firebase Console
3. Enable Push Notifications capability in Xcode
4. Test on physical device

#### Build Configuration

```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

### Web Deployment

#### Build Configuration

```bash
# Production build
ng build --configuration production

# Verify Service Worker is included in dist/
ls dist/firebase-messaging-sw.js
```

#### Server Configuration

Ensure the server serves:
- `firebase-messaging-sw.js` from root path
- Proper MIME types for JavaScript files
- HTTPS (required for Service Workers and notifications)

**nginx configuration**:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    root /var/www/frontend/dist;
    index index.html;
    
    # Serve Service Worker from root
    location /firebase-messaging-sw.js {
        add_header Cache-Control "no-cache";
        try_files $uri =404;
    }
    
    # Angular routing
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

#### Firebase Console Configuration

1. Add web app to Firebase project
2. Generate VAPID key for web push
3. Update `firebase.config.ts` with correct values
4. Whitelist domain in Firebase Console

### Monitoring and Alerts

#### Metrics to Monitor

1. **Notification Success Rate**: Percentage of successfully delivered notifications
2. **Token Registration Rate**: Number of new tokens registered per day
3. **Token Cleanup Rate**: Number of invalid tokens removed per day
4. **FCM API Latency**: Average time to send notification via FCM
5. **Error Rate**: Number of notification failures per hour

#### Logging Configuration

```python
# Configure structured logging
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

# Apply to notification logger
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger('app.services.notification_service')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

#### Alert Configuration

Set up alerts for:
- Notification success rate drops below 90%
- FCM API returns 5xx errors
- Token registration failures exceed threshold
- Service Worker registration failures on web

## Security Considerations

### Token Security

1. **Token Storage**: FCM tokens are stored in database with foreign key to user
2. **Token Validation**: Tokens are validated on each use, invalid tokens are removed
3. **Token Reassignment**: If a token is registered by a different user, it's reassigned (device changed hands)
4. **Token Expiration**: Inactive tokens (90+ days) are automatically removed

### Authentication

1. **API Endpoints**: All notification endpoints require authentication
2. **Token Registration**: Only authenticated users can register tokens
3. **Token Ownership**: Users can only unregister their own tokens

### Data Privacy

1. **Notification Content**: Avoid sending sensitive data in notification payload
2. **User Consent**: Request notification permissions explicitly
3. **Data Retention**: Remove tokens when user deletes account
4. **GDPR Compliance**: Allow users to opt-out of notifications

### Firebase Security

1. **Service Account**: Use service account with minimal required permissions
2. **Credentials**: Store Firebase credentials securely (environment variables, secrets manager)
3. **API Keys**: Restrict API keys to specific domains/apps in Firebase Console
4. **VAPID Key**: Keep VAPID key secure, rotate if compromised

## Future Enhancements

### Notification Preferences (Requirement 29)

Allow users to control which notification types they receive:

```typescript
interface NotificationPreferences {
  nueva_solicitud: boolean;
  solicitud_cancelada: boolean;
  diagnostico_completado: boolean;
  solicitud_aceptada: boolean;
  tecnico_asignado: boolean;
  cambio_estado: boolean;
  servicio_finalizado: boolean;
}
```

### Rich Notifications

Add images, action buttons, and custom layouts:

```json
{
  "notification": {
    "title": "Técnico en Camino",
    "body": "Juan Pérez está en camino a tu ubicación",
    "image": "https://example.com/technician-photo.jpg"
  },
  "android": {
    "notification": {
      "click_action": "OPEN_SERVICE_DETAIL",
      "icon": "notification_icon",
      "color": "#2196F3"
    }
  }
}
```

### Notification History

Store notification history in database for user reference:

```sql
CREATE TABLE historial_notificaciones (
    id SERIAL PRIMARY KEY,
    id_persona INTEGER REFERENCES persona(id),
    tipo VARCHAR(50),
    titulo TEXT,
    mensaje TEXT,
    datos JSONB,
    leida BOOLEAN DEFAULT FALSE,
    fecha_envio TIMESTAMP DEFAULT NOW(),
    fecha_lectura TIMESTAMP
);
```

### Push Notification Analytics

Track notification engagement:
- Delivery rate
- Open rate
- Click-through rate
- Time to open
- User engagement by notification type

### Scheduled Notifications

Send notifications at specific times:
- Reminder notifications
- Scheduled maintenance alerts
- Promotional notifications

### Notification Batching

Group multiple notifications into a single message:
- "You have 3 new service requests"
- Reduce notification fatigue
- Improve user experience

## Conclusion

This design document provides a comprehensive blueprint for implementing push notifications across the vehicle assistance platform. The implementation follows these key principles:

1. **Reliability**: Robust error handling, retry logic, and graceful degradation
2. **Scalability**: Support for multiple devices per user and efficient token management
3. **Consistency**: Unified notification structure across mobile and web platforms
4. **Maintainability**: Clean architecture with reusable services and clear integration points
5. **User Experience**: Timely notifications at every critical workflow moment

The implementation is divided into three main phases:
1. **Backend Enhancement**: Add missing notification methods for workshops
2. **Mobile Integration**: Connect notification handlers to navigation
3. **Web Implementation**: Full Firebase integration from scratch

Each component is designed to work independently while maintaining consistency in notification behavior and payload structure. The system is production-ready with comprehensive error handling, logging, and monitoring capabilities.
