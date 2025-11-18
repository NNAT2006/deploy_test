from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings
from .models import CourseRating
from django.contrib.auth import get_user_model
User = get_user_model()
# --- I. IMPORT CÁC MODELS VÀ LÔ-GIC CẦN THIẾT ---
try:
    from .tasks import send_study_reminders_for_course
except ImportError:
    def send_study_reminders_for_course(course_id):
        print(f"Placeholder: Sending reminders for course {course_id}")

from .models import (
    User, UserProfile, Course, Enrollment, Lesson, Question, Choice, LessonProgress,
    MockExam, MockQuestion, MockChoice, ExamAttempt,
    SpeakingSubmission, WritingSubmission, SentEmail,
    UserActivityLog
)

try:
    from .admin_site import admin_site
except ImportError:
    admin_site = admin.site


# --- II. INLINE CLASSES ---
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

class MockChoiceInline(admin.TabularInline):
    model = MockChoice
    extra = 4


# --- III. ADMIN CLASSES ---
@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'course')
    search_fields = ('course__title', 'user__username')
    readonly_fields = ('created_at',)

class MyUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_info', 'get_enrolled_count', 'get_lessons_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    inlines = [LessonInline]
    fieldsets = (
        ('Thông tin khóa học', {'fields': ('title', 'description', 'image'), 'classes': ('wide',)}),
        ('Thống kê', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )
    readonly_fields = ('created_at',)
    actions = ['send_reminders_for_selected']

    def course_info(self, obj):
        image_html = ''
        if obj.image:
            image_html = format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;margin-right:10px">', obj.image.url)
        return format_html(
            '<div style="display:flex;align-items:center">{}<div><strong style="font-size:1.1em">{}</strong><br>'
            '<span style="color:#666">{}</span></div></div>',
            image_html, obj.title,
            obj.description[:100]+'...' if len(obj.description)>100 else obj.description
        )
    course_info.short_description = 'Khóa học'

    def get_lessons_count(self, obj):
        return format_html('<span class="badge" style="background:#1a73e8">{} bài học</span>', obj.lessons.count())
    get_lessons_count.short_description = 'Bài học'

    def get_enrolled_count(self, obj):
        return format_html('<span class="badge" style="background:#34a853">{} học viên</span>', obj.enrolled_users.count())
    get_enrolled_count.short_description = 'Học viên đăng ký'

    def send_reminders_for_selected(self, request, queryset):
        count = 0
        for course in queryset:
            send_study_reminders_for_course(course.id)
            count += 1
        self.message_user(request, _('%d reminder job(s) queued or executed.') % count, level=messages.SUCCESS)
    send_reminders_for_selected.short_description = 'Gửi nhắc nhở học tập cho khóa học đã chọn'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title','course','order','get_questions_count','video')
    list_filter = ('course',)
    search_fields = ('title','course__title')
    inlines = [QuestionInline]
    ordering = ['course','order']

    def get_questions_count(self,obj):
        return obj.questions.count()
    get_questions_count.short_description = 'Số câu hỏi'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text','lesson','order')
    list_filter = ('lesson__course','lesson')
    search_fields = ('question_text',)
    inlines = [ChoiceInline]
    ordering = ['lesson','order']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user','course','enrolled_at')
    list_filter = ('course','enrolled_at')
    search_fields = ('user__username','course__title')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user','lesson','completed','score','completed_at')
    list_filter = ('completed','lesson__course')
    search_fields = ('user__username','lesson__title')


@admin.register(MockExam)
class MockExamAdmin(admin.ModelAdmin):
    list_display = ('title','exam_type_display','skill_display','question_count','created_at')
    list_filter = ('exam_type','skill','created_at')
    search_fields = ('title','description')
    fieldsets = (
        ('Thông tin cơ bản', {'fields':('title','exam_type','skill')}),
        ('Mô tả chi tiết', {'fields':('description',),'classes':('collapse',)}),
    )

    def exam_type_display(self,obj):
        return format_html('<span class="badge" style="background:{}">{}</span>','#1a73e8 if obj.exam_type=="ielts" else #34a853', obj.get_exam_type_display())
    exam_type_display.short_description = 'Loại bài thi'

    def skill_display(self,obj):
        colors={'listening':'#fbbc04','speaking':'#ea4335','reading':'#1a73e8','writing':'#34a853'}
        return format_html('<span class="badge" style="background:{}">{}</span>', colors.get(obj.skill,'#666'), obj.get_skill_display())
    skill_display.short_description='Kỹ năng'

    def question_count(self,obj):
        return obj.questions.count()
    question_count.short_description='Số câu hỏi'


@admin.register(MockQuestion)
class MockQuestionAdmin(admin.ModelAdmin):
    list_display=('text','exam_info','order','has_sample_answer','media_preview')
    list_filter=('exam__exam_type','exam__skill')
    search_fields=('text','exam__title')
    fields=('exam','text','order',('media_file','media_preview'),'sample_answer')
    readonly_fields=('media_preview',)
    inlines=[MockChoiceInline]

    def exam_info(self,obj):
        return format_html('<strong>{}</strong><br><span style="color:#666">{} - {}</span>', obj.exam.title,obj.exam.get_exam_type_display(),obj.exam.get_skill_display())
    exam_info.short_description='Bài thi'

    def has_sample_answer(self,obj):
        return bool(getattr(obj,'sample_answer',None))
    has_sample_answer.short_description='Có câu mẫu'
    has_sample_answer.boolean=True

    def media_preview(self,obj):
        if not obj.media_file: return "Không có tệp"
        if obj.media_file.name.lower().endswith(('.png','.jpg','.jpeg','.gif')):
            return format_html('<img src="{}" style="max-height:100px; max-width:300px;">', obj.media_file.url)
        if obj.media_file.name.lower().endswith(('.mp3','.wav','.ogg')):
            return format_html('<audio controls style="max-width:300px"><source src="{}"></audio>', obj.media_file.url)
        return format_html('<a href="{}">Tải xuống tệp</a>', obj.media_file.url)
    media_preview.short_description='Xem trước'


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display=('user','exam','score','created_at')
    list_filter=('exam','created_at')
    search_fields=('user__username','exam__title')


@admin.register(SpeakingSubmission)
class SpeakingSubmissionAdmin(admin.ModelAdmin):
    list_display=('user','question','reviewed','score','created_at')
    list_filter=('reviewed','created_at')
    search_fields=('user__username','question__text')


@admin.register(WritingSubmission)
class WritingSubmissionAdmin(admin.ModelAdmin):
    list_display=('user','question','reviewed','score','created_at')
    list_filter=('reviewed','created_at')
    search_fields=('user__username','question__text')


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display=('user','action','timestamp','course_link','details')
    list_filter=('action','timestamp','course')
    search_fields=('user__username','details')
    readonly_fields=('user','action','timestamp','details','course')

    def course_link(self,obj):
        if obj.course:
            try:
                url=reverse(f"admin:{obj.course._meta.app_label}_course_change", args=[obj.course.id])
                return format_html("<a href='{}'>{}</a>", url,obj.course.title)
            except:
                return obj.course.title
        return "-"
    course_link.short_description='Khóa học'


# --- IV. SentEmailAdmin ---
@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ('to_email','subject','course','sent_at','status')
    list_filter=('status','sent_at','course')
    search_fields=('to_email','subject','body')
    readonly_fields=('sent_at','body')
    actions=['resend_selected_emails']

    def resend_selected_emails(self,request,queryset):
        from django.core.mail import send_mail
        resent_count=0
        error_count=0
        for sent_email in queryset:
            try:
                send_mail(
                    subject=sent_email.subject,
                    message='',
                    html_message=sent_email.body,
                    from_email=getattr(settings,'DEFAULT_FROM_EMAIL',None),
                    recipient_list=[sent_email.to_email],
                    fail_silently=False,
                )
                SentEmail.objects.create(
                    to_email=sent_email.to_email,
                    subject=sent_email.subject+' (Resent)',
                    body=sent_email.body,
                    course=sent_email.course,
                    status='sent'
                )
                resent_count+=1
            except Exception as exc:
                error_count+=1
                SentEmail.objects.create(
                    to_email=sent_email.to_email,
                    subject=sent_email.subject+' (Resent - Failed)',
                    body=str(exc)[:200],
                    course=sent_email.course,
                    status=f'error: {type(exc).__name__}'
                )
        self.message_user(request,_('%d email(s) resent successfully. %d error(s).') % (resent_count,error_count),
                          level=messages.SUCCESS if error_count==0 else messages.WARNING)
    resend_selected_emails.short_description='Gửi lại email đã chọn'


# --- V. USER SOCIAL AUTH ---
from social_django.models import UserSocialAuth
try:
    admin_site.unregister(UserSocialAuth)
except: pass

class UserSocialAuthAdmin(admin.ModelAdmin):
    list_display = ("user_display","provider","uid","created")
    list_filter = ("provider",)
    search_fields = ("user__username","uid")
    readonly_fields=("user","provider","uid","created","extra_data")
    fieldsets=(
        ("Liên kết đăng nhập", {"fields":("user","provider","uid","created")}),
        ("Dữ liệu bổ sung", {"fields":("extra_data",),"classes":("collapse",)}),
    )

    def user_display(self, obj):
        # Nếu bạn muốn hiển thị username:
        return obj.user.username
        # Nếu bạn muốn hiển thị full name:
        # return obj.user.get_full_name() or obj.user.username
    user_display.short_description = "Người dùng"


admin_site.register(UserSocialAuth,UserSocialAuthAdmin)


# --- VI. ĐĂNG KÝ CÁC MODEL VỚI CUSTOM ADMIN SITE ---
try:
    admin_site.register(UserActivityLog,UserActivityLogAdmin)
    admin_site.register(SentEmail,SentEmailAdmin)
    admin_site.register(CourseRating, CourseRatingAdmin)
    admin_site.register(Course,CourseAdmin)
    admin_site.register(Lesson,LessonAdmin)
    admin_site.register(Question,QuestionAdmin)
    admin_site.register(Enrollment,EnrollmentAdmin)
    admin_site.register(LessonProgress,LessonProgressAdmin)
    admin_site.register(MockExam,MockExamAdmin)
    admin_site.register(MockQuestion,MockQuestionAdmin)
    admin_site.register(ExamAttempt,ExamAttemptAdmin)
    admin_site.register(SpeakingSubmission,SpeakingSubmissionAdmin)
    admin_site.register(WritingSubmission,WritingSubmissionAdmin)
    admin_site.register(User,MyUserAdmin)
except:
    pass
