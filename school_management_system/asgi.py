import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import schoolapp.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management_system.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(schoolapp.routing.websocket_urlpatterns)
#     ),
# })

application = get_asgi_application()
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            schoolapp.routing.websocket_urlpatterns
        )
    ),
})