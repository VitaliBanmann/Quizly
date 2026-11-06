"""API views for quizzes."""
from rest_framework.generics import (ListCreateAPIView,
                                     RetrieveUpdateDestroyAPIView)
from rest_framework.permissions import IsAuthenticated

from quizzes.models import Quiz

from .permissions import IsQuizOwner
from .serializers import (QuizCreateSerializer, QuizListSerializer,
                          QuizSerializer)


class QuizListCreateAPIView(ListCreateAPIView):
    """List the own quizzes or create a new one from a YouTube url."""

    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user).order_by(
            '-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuizCreateSerializer
        return QuizListSerializer


class QuizDetailAPIView(RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update or delete a quiz of the own user."""

    queryset = Quiz.objects.all()
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return QuizListSerializer
        return QuizSerializer
