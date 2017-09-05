from .models import Question


def trending(request):
    return {
        'top_questions': Question.objects.order_by('-votes')[:20]
    }
