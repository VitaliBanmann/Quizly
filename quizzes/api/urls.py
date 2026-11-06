from django.urls import path

from .views import QuizDetailAPIView, QuizListCreateAPIView

urlpatterns = [
    path('quizzes/', QuizListCreateAPIView.as_view(), name='quiz-list'),
    path('quizzes/<int:pk>/', QuizDetailAPIView.as_view(), name='quiz-detail'),
]
