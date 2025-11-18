from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import Registerform, UserProfileForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.base import ContentFile
import base64
import uuid
from django.utils import timezone
import requests
import json
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from .tasks import send_study_reminders
import logging
from django.urls import reverse
# IMPORT TẤT CẢ CÁC MODEL CẦN THIẾT
from .models import (
    Course, Enrollment, Lesson, Question, Choice, LessonProgress, UserProfile,
    MockExam, MockQuestion, MockChoice, ExamAttempt, SpeakingSubmission, WritingSubmission,
    UserActivityLog
)

logger = logging.getLogger(__name__)

# Ví dụ: courses/views.py hoặc file views.py chứa hàm home

from django.shortcuts import render
from django.db.models import Avg  # Import hàm tính trung bình
# Đảm bảo bạn import các Model Course và CourseRating từ file models.py tương ứng
from .models import Course, CourseRating  # Cần thay thế bằng đường dẫn chính xác của bạn
from django.db import models

def home(request):
    # 1. Truy vấn tất cả các Khóa học.
    #    Sử dụng annotate() để tính điểm trung bình (average_rating)
    #    và số lượng đánh giá (rating_count) cho mỗi khóa học NGAY TRONG truy vấn.
    courses = Course.objects.annotate(
        # Tính điểm trung bình từ các đánh giá liên quan
        average_rating=Avg('ratings__rating'),
        # Đếm số lượng đánh giá
        rating_count=models.Count('ratings')
    ).all()

    # 2. Chuẩn bị Context
    context = {
        'courses': courses,
        # Nếu bạn có các biến context khác cho trang chủ, hãy thêm chúng vào đây
    }

    # 3. Render template với dữ liệu đã chuẩn bị
    return render(request, 'home.html', context)


@login_required
def profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hồ sơ đã được cập nhật thành công!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'html/profile.html', {
        'form': form,
        'profile': profile
    })


# view dang ky & dang nhap user

# Dang ky
def register(request):
    if request.method == 'POST':
        form = Registerform(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            # GHI LOG: Đăng ký thành công
            UserActivityLog.objects.create(
                user=user,
                action='login',  # Thay vì 'register', dùng 'login' hoặc 'signup' để log user mới
                details='Đăng ký tài khoản thành công.'
            )
            messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
            return redirect('accounts:login')
    else:
        form = Registerform()
    return render(request, 'html/register.html', {'form': form})


# Dang nhap user
def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # GHI LOG: Đăng nhập
            UserActivityLog.objects.create(
                user=user,
                action='login',
                details='Đăng nhập thành công qua form.'
            )
            return redirect('accounts:user_dashboard')
        else:
            # Bạn có thể ghi log thất bại nếu muốn, nhưng thường không làm
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng')
            return render(request, 'html/login.html', {
                'error_message': 'Tên đăng nhập hoặc mật khẩu không đúng'
            })
    return render(request, 'html/login.html')


# Dang xuat user
def logout_user(request):
    # Kiểm tra xem người dùng đã đăng nhập chưa trước khi ghi log
    if request.user.is_authenticated:
        # GHI LOG: Đăng xuất
        UserActivityLog.objects.create(
            user=request.user,
            action='logout',
            details='Đăng xuất.'
        )
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('accounts:home')


# Tao dashboard cho admin va user Đoạn @login_required giúp chỉ người đăng nhập mới xem được.

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('accounts:user_dashboard')
    return render(request, 'admin_dashboard.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def trigger_send_reminders(request):
    """Admin-only endpoint to trigger the study reminder task.
    Returns JSON with status.
    """
    try:
        # ưu tiên async nếu Celery worker khả dụng
        try:
            send_study_reminders.delay()
            return JsonResponse({'status': 'queued'})
        except Exception:
            # fallback: chạy đồng bộ
            send_study_reminders()
            return JsonResponse({'status': 'sent_sync'})
    except Exception as e:
        logger.error(f"Lỗi khi kích hoạt reminder: {e}")
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=500)


@login_required
def user_dashboard(request):
    all_courses = Course.objects.all()
    enrolled_courses = Course.objects.filter(enrolled_users=request.user)
    return render(request, 'user_dashboard.html', {
        'courses': all_courses,
        'enrolled_courses': enrolled_courses
    })


@login_required
def home_after_login(request):
    return render(request, "home.html")


class userloginview(LoginView):
    template_name = 'html/login.html'  # Đảm bảo đúng template
    redirect_authenticated_user = True


@login_required
def enroll_course(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        # Kiểm tra xem đã đăng ký chưa
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course
        )
        if created:
            # GHI LOG: Đăng ký khóa học
            UserActivityLog.objects.create(
                user=request.user,
                action='enroll_course',
                course=course,
                details=f'Đã đăng ký khóa học: {course.title}'
            )
            messages.success(request, f'Bạn đã đăng ký khóa học "{course.title}" thành công.')
        else:
            messages.info(request, f'Bạn đã đăng ký khóa học "{course.title}" rồi.')

        # Kiểm tra request có từ trang detail không
        referer = request.META.get('HTTP_REFERER', '')
        if 'course/{}'.format(course_id) in referer:
            return redirect('accounts:course_detail', course_id=course_id)
        return redirect('accounts:user_dashboard')
    return redirect('accounts:course_detail', course_id=course_id)


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    lessons = course.lessons.all().order_by('order')

    # Lấy tiến độ học tập cho mỗi bài học
    lesson_progress = {}
    if is_enrolled:
        for lesson in lessons:
            progress = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
            if progress:
                lesson_progress[lesson.id] = {
                    'completed': progress.completed,
                    'score': progress.score
                }
    # Compute total estimated duration (default 45 min per lesson)
    total_duration = lessons.count() * 45

    # Compute user's course progress percentage (completed lessons / total)
    progress_percent = 0
    if lessons.count() > 0:
        completed_count = sum(1 for v in lesson_progress.values() if v.get('completed'))
        progress_percent = int((completed_count / lessons.count()) * 100)

    # Number of enrolled users
    enrolled_count = course.enrolled_users.count()

    return render(request, 'course_detail.html', {
        'course': course,
        'is_enrolled': is_enrolled,
        'lessons': lessons,
        'lesson_progress': lesson_progress,
        'total_duration': total_duration,
        'progress_percent': progress_percent,
        'enrolled_count': enrolled_count,
    })


@login_required
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    # Kiểm tra xem người dùng đã đăng ký khóa học chưa
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, 'Bạn cần đăng ký khóa học này để xem bài học.')
        return redirect('accounts:course_detail', course_id=course_id)

    # Lấy tất cả câu hỏi và lựa chọn cho bài học
    questions = lesson.questions.all().order_by('order')
    choices = {q.id: q.choices.all() for q in questions}

    # Lấy hoặc tạo tiến độ bài học
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    # Get all lessons for the sidebar
    all_lessons = course.lessons.all().order_by('order')

    # Get progress for all lessons
    lesson_progress = {}
    for l in all_lessons:
        prog = LessonProgress.objects.filter(user=request.user, lesson=l).first()
        if prog:
            lesson_progress[l.id] = {
                'completed': prog.completed,
                'score': prog.score
            }

    return render(request, 'html/lesson_view.html', {
        'course': course,
        'lesson': lesson,
        'current_lesson': lesson,
        'lessons': all_lessons,
        'lesson_progress': lesson_progress,
        'debug': True,
        'questions': questions,
        'choices': choices,
        'progress': progress
    })


@login_required
@require_POST
def submit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    answers = request.POST.dict()
    del answers['csrfmiddlewaretoken']

    # Tính điểm
    total_questions = lesson.questions.count()
    correct_answers = 0

    for question_id, answer_id in answers.items():
        try:
            # Đảm bảo question_id là số nguyên và bắt đầu bằng 'question_'
            if question_id.startswith('question_'):
                q_id = int(question_id.replace('question_', ''))
                question = Question.objects.get(id=q_id)
                choice = Choice.objects.get(id=int(answer_id), question=question)
                if choice.is_correct:
                    correct_answers += 1
        except (Question.DoesNotExist, Choice.DoesNotExist, ValueError):
            logger.warning(f"Invalid answer submission: q_id={question_id}, ans_id={answer_id}")

    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Cập nhật tiến độ
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )
    # Kiểm tra tiến độ cũ để chỉ ghi log một lần khi hoàn thành bài học (score >= 50)
    is_completed_now = (progress.completed == False) and (score >= 50)

    progress.score = score
    progress.completed = (score >= 50)  # Cập nhật trạng thái hoàn thành dựa trên điểm số

    # Chỉ cập nhật completed_at nếu chưa hoàn thành trước đó và bây giờ đã hoàn thành
    if is_completed_now:
        progress.completed_at = timezone.now()

    progress.save()

    # GHI LOG: Hoàn thành bài học
    if is_completed_now:
        UserActivityLog.objects.create(
            user=request.user,
            action='complete_lesson',
            course=lesson.course,
            details=f'Hoàn thành bài học "{lesson.title}" với điểm số {progress.score:.1f}.'
        )

    return JsonResponse({
        'score': score,
        'correct_answers': correct_answers,
        'total_questions': total_questions
    })


@login_required
@require_POST
def retry_lesson(request, lesson_id):
    """Reset the user's progress for a lesson so they can retake it."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    progress = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()

    if progress and progress.completed:  # Chỉ ghi log nếu có tiến độ để reset
        # GHI LOG: Thử lại bài học
        UserActivityLog.objects.create(
            user=request.user,
            action='retry_lesson',
            course=lesson.course,
            details=f'Thử lại bài học "{lesson.title}".'
        )

        progress.completed = False
        progress.score = 0
        progress.completed_at = None
        progress.save()
    elif progress:
        progress.score = 0
        progress.save()

    messages.info(request, f'Đã đặt lại tiến độ bài học "{lesson.title}".')
    return redirect('accounts:lesson_detail', course_id=lesson.course.id, lesson_id=lesson.id)


@login_required
def my_courses(request):
    enrolled_courses = Course.objects.filter(enrolled_users=request.user)
    return render(request, 'my_courses.html', {
        'enrolled_courses': enrolled_courses
    })


@login_required
def progress_overview(request):
    """Render a dedicated page showing the user's progress across enrolled courses."""
    courses = Course.objects.filter(enrolled_users=request.user).distinct()
    progress_list = []
    for course in courses:
        total = course.lessons.count()
        if total == 0:
            percent = 0
            completed = 0
        else:
            completed = LessonProgress.objects.filter(
                user=request.user,
                lesson__course=course,
                completed=True
            ).count()
            percent = int((completed / total) * 100)

        progress_list.append({
            'id': course.id,
            'title': course.title,
            'percent': percent,
            'completed': completed,
            'total': total,
            'url': reverse('accounts:course_detail', args=[course.id])
        })

    return render(request, 'html/progress_overview.html', {
        'user_progress': progress_list
    })


@login_required
def mock_exams_list(request):
    """List available mock exams grouped by type and skill."""
    exams = MockExam.objects.all().order_by('exam_type', 'skill', 'title')
    return render(request, 'html/mock_exams_list.html', {
        'exams': exams
    })


@login_required
def take_mock_exam(request, exam_id):
    exam = get_object_or_404(MockExam, id=exam_id)
    questions = exam.questions.prefetch_related('choices').all().order_by('order')  # Đảm bảo thứ tự
    return render(request, 'html/take_mock_exam.html', {
        'exam': exam,
        'questions': questions
    })


@login_required
@require_POST
def submit_mock_exam(request, exam_id):
    exam = get_object_or_404(MockExam, id=exam_id)
    questions = exam.questions.all()
    total = questions.count()
    if total == 0:
        messages.error(request, 'Bài thi trống.');
        return redirect('accounts:mock_exams_list')

    # Handle auto-graded (choice) questions and collect speaking/writing submissions
    auto_total = 0
    auto_correct = 0
    speaking_scores = []
    submission_success = False

    for q in questions:
        # Auto-graded multiple-choice
        ans = request.POST.get(f'question_{q.id}')
        if ans is not None and q.choices.exists():
            auto_total += 1
            if ans:
                try:
                    choice = MockChoice.objects.get(id=int(ans), question=q)
                    if choice.is_correct:
                        auto_correct += 1
                except (MockChoice.DoesNotExist, ValueError):
                    pass

        # Speaking: base64 audio data upload
        speaking_data = request.POST.get(f'speaking_q_{q.id}')
        speaking_score_val = None
        speaking_score_str = request.POST.get(f'speaking_score_{q.id}')

        if speaking_score_str:
            try:
                speaking_score_val = float(speaking_score_str)
                speaking_scores.append(speaking_score_val)
            except Exception:
                speaking_score_val = None

        if speaking_data:
            try:
                # speaking_data expected as data URL: data:audio/webm;base64,XXXXX
                header, b64 = speaking_data.split(',', 1)
                file_data = base64.b64decode(b64)
                ext = 'webm'
                if 'mpeg' in header or 'mp3' in header:
                    ext = 'mp3'
                filename = f"speaking_{request.user.id}_{q.id}_{uuid.uuid4().hex[:8]}.{ext}"
                content = ContentFile(file_data, name=filename)

                SpeakingSubmission.objects.create(
                    user=request.user,
                    question=q,
                    audio=content,
                    score=speaking_score_val if speaking_score_val is not None else 0.0,
                    reviewed=speaking_score_val is not None
                )
                submission_success = True
            except Exception as e:
                logger.error(f'Error processing speaking submission: {e}')
                pass

        # Writing: text submission
        writing_text = request.POST.get(f'writing_q_{q.id}')
        if writing_text:
            WritingSubmission.objects.create(user=request.user, question=q, text=writing_text)
            submission_success = True

    # Compute a provisional/final score
    auto_percent = None
    if auto_total > 0:
        auto_percent = (auto_correct / auto_total) * 100

    speaking_avg = None
    if len(speaking_scores) > 0:
        speaking_avg = sum(speaking_scores) / len(speaking_scores)

    # Decide final score strategy
    if exam.skill in ['speaking', 'writing']:  # Chỉ chấm speaking/writing nếu đó là kỹ năng chính
        if exam.skill == 'speaking' and speaking_avg is not None:
            final_score = round(speaking_avg, 1)
        # Bỏ qua logic chấm điểm phức tạp cho writing vì cần chấm thủ công/AI khác.
        # Giữ điểm 0.0 nếu chỉ có writing và chưa được chấm
        elif exam.skill == 'writing':
            final_score = 0.0
        else:
            final_score = 0.0  # Mặc định nếu không có dữ liệu

    # Trường hợp mixed skill exam (hoặc listening/reading)
    elif auto_percent is not None:
        if speaking_avg is not None:
            # Nếu có cả tự động (reading/listening) và speaking
            final_score = round((auto_percent * exam.auto_weight) + (speaking_avg * exam.manual_weight), 1)
        else:
            final_score = round(auto_percent, 1)
    else:
        final_score = 0.0

    attempt = ExamAttempt.objects.create(
        user=request.user,
        exam=exam,
        score=final_score,
        max_score=100.0
    )

    # GHI LOG: Nộp bài thi thử
    UserActivityLog.objects.create(
        user=request.user,
        action='submit_exam',
        details=f'Nộp bài thi thử "{exam.title}" (kỹ năng {exam.get_skill_display()}) với điểm sơ bộ: {final_score:.1f}.'
    )
    messages.success(request, f'Bạn đã nộp bài thi thử "{exam.title}" thành công. Điểm sơ bộ: {final_score:.1f}/100.')

    # Redirect to scores page where the new attempt will appear
    return redirect('accounts:scores_page')


@login_required
def scores_page(request):
    attempts = ExamAttempt.objects.filter(user=request.user).select_related('exam').order_by('-created_at')
    return render(request, 'html/scores.html', {
        'attempts': attempts
    })


@login_required
def skills(request):
    """Show user's skills/certificates for completed courses."""
    completed = []
    courses = Course.objects.filter(enrolled_users=request.user).distinct()
    for course in courses:
        lessons = course.lessons.all()
        total = lessons.count()
        if total == 0:
            continue

        completed_count = LessonProgress.objects.filter(
            user=request.user,
            lesson__course=course,
            completed=True
        ).count()

        if completed_count >= total:
            last = LessonProgress.objects.filter(user=request.user, lesson__course=course, completed=True).order_by(
                '-completed_at').first()
            completed.append({
                'id': course.id,
                'title': course.title,
                'completed_at': last.completed_at if last else None,
                'url': reverse('accounts:certificate_view', args=[course.id])
            })

    return render(request, 'html/skills.html', {
        'certificates': completed
    })


@login_required
def certificate_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # ensure user completed the course
    lessons = course.lessons.all()
    total = lessons.count()
    completed_count = LessonProgress.objects.filter(user=request.user, lesson__course=course, completed=True).count()
    if total == 0 or completed_count < total:
        messages.error(request, 'Bạn chưa hoàn thành khóa học này, không thể xem chứng chỉ.')
        return redirect('accounts:skills')

    last = LessonProgress.objects.filter(user=request.user, lesson__course=course, completed=True).order_by(
        '-completed_at').first()
    return render(request, 'html/certificate.html', {
        'course': course,
        'user': request.user,
        'completed_at': last.completed_at if last else None,
    })


# 🛠️ START: HÀM AI CHAT ĐÃ ĐƯỢC SỬA LỖI VÀ TỐI ƯU
@require_POST
def ai_chat_api(request):
    """Handles POST requests for AI chat analysis and enforces Vietnamese output."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'not_authenticated', 'message': 'Bạn cần đăng nhập để sử dụng chat.'}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.exception('Invalid JSON in ai_chat_api request')
        return JsonResponse({'error': 'invalid_json', 'message': 'Dữ liệu yêu cầu không hợp lệ (JSON)'}, status=400)

    message = payload.get('text')
    if not message:
        return JsonResponse({'error': 'no_message', 'message': 'Vui lòng cung cấp văn bản để phân tích.'}, status=400)

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    api_url = getattr(settings, 'GEMINI_API_URL', None)

    # KIỂM TRA CẤU HÌNH API
    if not api_key:
        logger.error('GEMINI_API_KEY not set in settings.')
        return JsonResponse({
            'error': 'gemini_key_missing',
            'message': 'Lỗi Server (503): Dịch vụ AI không khả dụng (thiếu API Key).'
        }, status=503)

    if not api_url:
        logger.error('GEMINI_API_URL not set in settings.')
        return JsonResponse({
            'error': 'gemini_url_missing',
            'message': 'Lỗi Server (503): Dịch vụ AI không khả dụng (thiếu API URL).'
        }, status=503)

    # THIẾT LẬP PROMPT VÀ YÊU CẦU BẰNG TIẾNG VIỆT
    vietnamese_instruction = (
        "Bạn là một Trợ lý Ngôn ngữ AI (AI Tutor). Nhiệm vụ của bạn là phân tích lỗi ngữ pháp và từ vựng trong văn bản tiếng Anh. "
        "Hãy **LUÔN LUÔN** trả lời bằng tiếng Việt. Trong phản hồi, bạn phải: "
        "1. Cung cấp phiên bản tiếng Anh đã được sửa đúng (Correction). "
        "2. Giải thích lỗi và đề xuất cách cải thiện, **HOÀN TOÀN BẰNG TIẾNG VIỆT** (Explanation). "
        "3. Không sử dụng tiếng Anh trong phần giải thích. "
        "Văn bản tiếng Anh cần phân tích là: "
    )

    full_prompt = f"{vietnamese_instruction}\n\n{message}"

    url_with_key = f"{api_url}?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    try:
        resp = requests.post(url_with_key, headers=headers, json=body, timeout=45)
    except requests.RequestException as e:
        logger.exception('AI chat request to upstream failed')
        return JsonResponse({'error': 'request_failed', 'message': f'Không thể kết nối với dịch vụ AI: {str(e)}'},
                            status=502)

    # --- KHỐI XỬ LÝ LỖI HTTP TỪ GEMINI (ĐÃ CHỈNH SỬA) ---
    if resp.status_code != 200:
        try:
            # Cố gắng phân tích phản hồi JSON để lấy thông báo lỗi chi tiết
            rj = resp.json()
            error_msg = rj.get('error', {}).get('message', f'Lỗi API Gemini, Mã: {resp.status_code}')
        except Exception:
            # Xử lý trường hợp Gemini không trả về JSON hợp lệ (ví dụ: HTML lỗi)
            error_msg = f"Lỗi không xác định từ Gemini. Mã HTTP: {resp.status_code}. Thân phản hồi: {resp.text[:100]}..."

        logger.error('Gemini API returned error (Status: %d): %s', resp.status_code, error_msg)

        # TRẢ VỀ MÃ LỖI THỰC TẾ (400, 401, 403, 429...) HOẶC 500 NẾU KHÔNG CHẮC CHẮN
        # Điều này giúp người dùng/phát triển biết lỗi thực sự là gì.
        response_status = resp.status_code if 400 <= resp.status_code < 500 else 500

        return JsonResponse({
            'error': 'gemini_api_error',
            'message': f'Lỗi API Gemini. Mã: {resp.status_code}. Kiểm tra Khóa API, Hạn mức, và URL: {error_msg}'
        }, status=response_status)
    # --- KẾT THÚC KHỐI XỬ LÝ LỖI HTTP TỪ GEMINI ---

    # XỬ LÝ PHẢN HỒI JSON (STATUS 200 OK)
    try:
        rj = resp.json()
    except Exception:
        text_body = resp.text[:1000] if resp.text else 'Empty response body'
        logger.error('Failed parsing upstream JSON (Status: 200). Body snippet: %s', text_body)
        return JsonResponse({'error': 'invalid_response',
                             'message': 'Phân tích phản hồi API thành công nhưng nội dung JSON không hợp lệ.'},
                            status=502)

    # TRÍCH XUẤT VĂN BẢN
    text = None
    try:
        candidates = rj.get('candidates')
        if candidates and isinstance(candidates, list) and len(candidates) > 0:
            text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text')
    except Exception as e:
        logger.error(f'Error extracting text from Gemini response: {e}, Response: {rj}')

    if not text:
        logger.error('Gemini API response did not contain text content: %s', rj)
        return JsonResponse({'error': 'no_text_in_response', 'message': 'Phản hồi từ AI không chứa văn bản.'},
                            status=500)

    # TRẢ VỀ PHÂN TÍCH
    return JsonResponse({'analysis': text})


# 🛠️ END: HÀM AI CHAT ĐÃ ĐƯỢC SỬA LỖI VÀ TỐI ƯU

def ai_chat_status(request):
    """Simple status endpoint to help debug GEMINI configuration and connectivity."""
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    api_url = getattr(settings, 'GEMINI_API_URL', None)
    configured = bool(api_key and api_url)

    data = {
        'configured': configured,
        'api_url_present': bool(api_url),
        'api_key_present': bool(api_key),
    }

    if configured:
        url_with_key = f"{api_url}?key={api_key}"

        headers = {'Content-Type': 'application/json'}
        probe_body = {"contents": [{"role": "user", "parts": [{"text": "ping"}]}]}
        try:
            resp = requests.post(url_with_key, headers=headers, json=probe_body, timeout=90)
            data['upstream_status_code'] = resp.status_code

            body_snip = None
            try:
                body_text = resp.text
                body_snip = body_text[:800]
            except Exception:
                body_snip = None
            data['upstream_body_snippet'] = body_snip
            if resp.status_code < 200 or resp.status_code >= 300:
                data['ok'] = False
            else:
                data['ok'] = True
        except Exception as e:
            logger.exception('Probe to Gemini failed')
            data['probe_error'] = str(e)
            data['ok'] = False

    return JsonResponse(data)