from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.db.models import Avg
class UserActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Đăng nhập'),
        ('logout', 'Đăng xuất'),
        ('enroll_course', 'Đăng ký khóa học'),
        ('complete_lesson', 'Hoàn thành bài học'),
        ('submit_exam', 'Nộp bài thi thử'),
        ('view_page', 'Xem trang'), # Thêm nếu bạn muốn log việc xem trang chung
        # Bạn có thể thêm nhiều hành động khác ở đây
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True, null=True)
    # Có thể liên kết với một Model cụ thể (ví dụ: Course, Lesson, MockExam)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'UserActivityHistory'
        verbose_name_plural = 'UserActivityHistory'

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.user.username} - {self.get_action_display()}"
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='profile_images/', default='profile_images/default.png')
    full_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    enrolled_users = models.ManyToManyField(User, through='Enrollment', related_name='enrolled_courses')

    def __str__(self):
        return self.title

    def get_average_rating(self):
        """Tính điểm trung bình của khóa học."""
        # Truy vấn tất cả đánh giá của khóa học này và tính điểm trung bình (Avg)
        average = self.ratings.aggregate(Avg('rating'))['rating__avg']

        # Làm tròn kết quả
        if average is not None:
            return round(average, 1)  # Làm tròn đến 1 chữ số thập phân
        return 0.0

    def get_rating_count(self):
        """Đếm số lượng đánh giá."""
        return self.ratings.count()


class CourseRating(models.Model):
    # Khóa ngoại đến Model Course
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ratings')

    # Khóa ngoại đến Model User (người đánh giá)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Số sao (từ 1 đến 5)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Đánh giá từ 1 đến 5 sao."
    )

    # Nội dung đánh giá (tùy chọn)
    comment = models.TextField(blank=True, null=True)

    # Thời gian tạo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Đảm bảo mỗi người dùng chỉ đánh giá 1 lần cho 1 khóa học
        unique_together = ('course', 'user')

        verbose_name_plural = "CourseRating"

    def __str__(self):
        return f'{self.user.username} - {self.course.title} ({self.rating} sao)'

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    # Optional short video for the lesson (uploaded file)
    video = models.FileField(upload_to='lesson_videos/', null=True, blank=True)
    order = models.IntegerField(default=0)  # Thứ tự bài học
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    image = models.ImageField(upload_to='question_images/', null=True, blank=True)
    order = models.IntegerField(default=0)  # Thứ tự câu hỏi

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question_text

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'course']

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'lesson']


class MockExam(models.Model):
    EXAM_TYPES = (
        ('ielts', 'IELTS'),
        ('toeic', 'TOEIC'),
    )
    SKILLS = (
        ('listening', 'Nghe'),
        ('speaking', 'Nói'),
        ('reading', 'Đọc'),
        ('writing', 'Viết'),
    )
    LANGUAGES = (
        ('en-US', 'English (US)'),
        ('en-GB', 'English (UK)'),
        ('en-AU', 'English (Australia)'),
    )

    title = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)
    skill = models.CharField(max_length=20, choices=SKILLS)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Cấu hình chấm điểm
    auto_weight = models.FloatField(default=0.7, help_text='Trọng số chấm tự động (0.0 - 1.0)')
    manual_weight = models.FloatField(default=0.3, help_text='Trọng số chấm tay (0.0 - 1.0)') 
    speech_language = models.CharField(max_length=10, choices=LANGUAGES, default='en-US',
                                    help_text='Ngôn ngữ sử dụng cho nhận dạng giọng nói')

    def __str__(self):
        return f"{self.get_exam_type_display()} - {self.get_skill_display()} - {self.title}"


class MockQuestion(models.Model):
    exam = models.ForeignKey(MockExam, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    order = models.IntegerField(default=0)
    media_file = models.FileField(upload_to='mock_media/', null=True, blank=True)
    # Optional sample answer text for speaking questions (used by Web Speech API comparison)
    sample_answer = models.TextField(null=True, blank=True, help_text='Sample answer text for speaking questions')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class MockChoice(models.Model):
    question = models.ForeignKey(MockQuestion, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class ExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(MockExam, on_delete=models.CASCADE)
    score = models.FloatField()
    max_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.exam} - {self.score}/{self.max_score}"


class SpeakingSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(MockQuestion, on_delete=models.CASCADE)
    audio = models.FileField(upload_to='speaking_submissions/')
    reviewed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Speaking {self.user.username} - {self.question.id}"


class WritingSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(MockQuestion, on_delete=models.CASCADE)
    text = models.TextField()
    reviewed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Writing {self.user.username} - {self.question.id}"


class SentEmail(models.Model):
    """Log mỗi email đã gửi để admin có thể xem lịch sử gửi."""
    to_email = models.CharField(max_length=320)
    subject = models.CharField(max_length=500)
    body = models.TextField(blank=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    sent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='sent')

    def __str__(self):
        return f"{self.to_email} - {self.subject} @ {self.sent_at:%Y-%m-%d %H:%M}"

    class Meta:
        verbose_name = 'Sent Email'
        verbose_name_plural = 'Sent Emails'