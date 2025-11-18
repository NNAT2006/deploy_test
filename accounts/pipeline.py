    # accounts/pipeline.py (NỘI DUNG ĐÃ SỬA)
from .models import UserActivityLog
from django.utils.text import slugify
from social_core.pipeline.partial import partial

# Thêm tham số 'backend' vào hàm
# backend là một instance của lớp SocialBackend, có thuộc tính name (ví dụ: 'google-oauth2')
def log_social_login(user, backend, response, details, **kwargs):
    """Ghi log khi người dùng đăng nhập lần đầu hoặc đăng nhập lại qua Social Auth."""
    if user and user.is_authenticated:
        # SỬA: Dùng thuộc tính .name của biến backend
        backend_name = backend.name if hasattr(backend, 'name') else 'social_auth'

        UserActivityLog.objects.create(
            user=user,
            action='login',
            details=f"Đăng nhập qua {backend_name}" # <<< ĐÃ SỬA
        )
    # Trả về các đối số để pipeline tiếp tục hoạt động
    # Cần trả về backend vì nó là một tham số bắt buộc trong các bước tiếp theo của pipeline
    return None

def create_username(strategy, backend, details, user=None, *args, **kwargs):
    # Nếu user đã tồn tại -> KHÔNG đổi username
    if user:
        return

    email = details.get('email')
    if not email:
        return

    username_base = email.split('@')[0]

    from django.contrib.auth import get_user_model
    User = get_user_model()

    new_username = username_base
    counter = 1

    # Xử lý trùng username
    while User.objects.filter(username=new_username).exists():
        new_username = f"{username_base}{counter}"
        counter += 1

    # Ghi username vào dữ liệu để create_user() sẽ dùng nó
    return {"username": new_username}

