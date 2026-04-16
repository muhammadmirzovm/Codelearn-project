import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone

from .models import TestPack, Question, Choice, GlobalTestAttempt, GlobalTestAnswer
from .forms import TestPackForm


def teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher:
            return HttpResponseForbidden('Teachers only.')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def test_list(request):
    user = request.user
    if user.is_teacher:
        packs = TestPack.objects.filter(created_by=user)
        return render(request, 'tests/test_list.html', {'packs': packs, 'is_teacher': True})

    # Students: show global tests only
    packs = TestPack.objects.filter(mode=TestPack.MODE_GLOBAL)
    attempts = {a.test_pack_id: a for a in GlobalTestAttempt.objects.filter(student=user).order_by('-started_at')}
    test_data = [{'pack': p, 'attempt': attempts.get(p.pk)} for p in packs]
    return render(request, 'tests/test_list.html', {'test_data': test_data, 'is_teacher': False})


@teacher_required
def test_create(request):
    if request.method == 'POST':
        form = TestPackForm(request.POST)
        if form.is_valid():
            pack = form.save(commit=False)
            pack.created_by = request.user
            pack.save()
            messages.success(request, 'Test paketi yaratildi!')
            return redirect('tests:questions', pk=pack.pk)
    else:
        form = TestPackForm()
    return render(request, 'tests/test_form.html', {'form': form, 'editing': False})


@teacher_required
def test_edit(request, pk):
    pack = get_object_or_404(TestPack, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = TestPackForm(request.POST, instance=pack)
        if form.is_valid():
            form.save()
            messages.success(request, 'Test yangilandi!')
            return redirect('tests:list')
    else:
        form = TestPackForm(instance=pack)
    return render(request, 'tests/test_form.html', {'form': form, 'editing': True, 'pack': pack})


@teacher_required
def test_delete(request, pk):
    pack = get_object_or_404(TestPack, pk=pk, created_by=request.user)
    if request.method == 'POST':
        pack.delete()
        messages.success(request, 'Test o\'chirildi.')
        return redirect('tests:list')
    return render(request, 'tests/test_confirm_delete.html', {'pack': pack})


@teacher_required
def test_detail(request, pk):
    pack = get_object_or_404(TestPack, pk=pk, created_by=request.user)
    questions = pack.questions.prefetch_related('choices').all()
    return render(request, 'tests/test_detail.html', {'pack': pack, 'questions': questions})


@teacher_required
def question_manage(request, pk):
    pack = get_object_or_404(TestPack, pk=pk, created_by=request.user)

    if request.method == 'POST':
        data = json.loads(request.body)
        questions_data = data.get('questions', [])

        # Validate minimum 5 questions
        if len(questions_data) < 5:
            return JsonResponse({'error': 'Kamida 5 ta savol bo\'lishi kerak!'}, status=400)

        pack.questions.all().delete()
        for i, q_data in enumerate(questions_data):
            question = Question.objects.create(
                test_pack=pack, text=q_data['text'], order=i + 1
            )
            for c_data in q_data['choices']:
                Choice.objects.create(
                    question=question,
                    label=c_data['label'],
                    text=c_data['text'],
                    is_correct=c_data['is_correct'],
                )
        return JsonResponse({'success': True, 'count': len(questions_data)})

    questions = pack.questions.prefetch_related('choices').all()
    return render(request, 'tests/question_manage.html', {'pack': pack, 'questions': questions})


# ── Global test (students) ────────────────────────────────────────────────────

@login_required
def global_test_join(request, pk):
    pack = get_object_or_404(TestPack, pk=pk, mode=TestPack.MODE_GLOBAL)
    user = request.user

    if not user.is_student:
        return HttpResponseForbidden('Students only.')

    # Check if time is up for global test
    if pack.duration_minutes > 0:
        latest = GlobalTestAttempt.objects.filter(
            test_pack=pack, student=user, status=GlobalTestAttempt.STATUS_ONGOING
        ).first()
        if latest:
            elapsed = (timezone.now() - latest.started_at).total_seconds()
            if elapsed > pack.duration_minutes * 60:
                latest.status      = GlobalTestAttempt.STATUS_FINISHED
                latest.finished_at = timezone.now()
                latest.score       = latest.answers.filter(is_correct=True).count()
                latest.total       = pack.question_count
                latest.save()
                return redirect('tests:global_results', pk=pk, attempt_pk=latest.pk)

    attempt, created = GlobalTestAttempt.objects.get_or_create(
        test_pack=pack, student=user,
        status=GlobalTestAttempt.STATUS_ONGOING,
        defaults={'total': pack.question_count}
    )
    if not created and attempt.status == GlobalTestAttempt.STATUS_FINISHED:
        # Start a new attempt
        attempt = GlobalTestAttempt.objects.create(
            test_pack=pack, student=user,
            status=GlobalTestAttempt.STATUS_ONGOING,
            total=pack.question_count
        )

    questions    = pack.questions.prefetch_related('choices').all()
    answered_ids = list(attempt.answers.values_list('question_id', flat=True))
    started_iso  = attempt.started_at.isoformat()

    return render(request, 'tests/global_test_join.html', {
        'pack':         pack,
        'attempt':      attempt,
        'questions':    questions,
        'answered_ids': answered_ids,
        'started_iso':  started_iso,
    })


@login_required
def global_test_answer(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    pack    = get_object_or_404(TestPack, pk=pk, mode=TestPack.MODE_GLOBAL)
    user    = request.user
    data    = json.loads(request.body)
    attempt = get_object_or_404(
        GlobalTestAttempt,
        pk=data.get('attempt_id'), test_pack=pack, student=user,
        status=GlobalTestAttempt.STATUS_ONGOING
    )
    question = get_object_or_404(Question, pk=data.get('question_id'), test_pack=pack)
    choice   = get_object_or_404(Choice, pk=data.get('choice_id'), question=question)

    GlobalTestAnswer.objects.update_or_create(
        attempt=attempt, question=question,
        defaults={'choice': choice, 'is_correct': choice.is_correct}
    )
    return JsonResponse({'success': True, 'answered': attempt.answers.count()})


@login_required
def global_test_finish(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    pack    = get_object_or_404(TestPack, pk=pk, mode=TestPack.MODE_GLOBAL)
    user    = request.user
    data    = json.loads(request.body)
    attempt = get_object_or_404(
        GlobalTestAttempt,
        pk=data.get('attempt_id'), test_pack=pack, student=user,
        status=GlobalTestAttempt.STATUS_ONGOING
    )

    score = attempt.answers.filter(is_correct=True).count()
    total = pack.question_count

    attempt.score       = score
    attempt.total       = total
    attempt.status      = GlobalTestAttempt.STATUS_FINISHED
    attempt.finished_at = timezone.now()
    attempt.save()

    coins_earned = 0
    # Coins only if 100% correct and never received before
    if score == total and total > 0 and pack.coin_reward > 0:
        already_rewarded = GlobalTestAttempt.objects.filter(
            test_pack=pack, student=user, coins_awarded=True
        ).exists()
        if not already_rewarded:
            from apps.users.models import CoinTransaction
            CoinTransaction.objects.create(
                user=user,
                amount=pack.coin_reward,
                tx_type=CoinTransaction.TYPE_EARN,
                note=f'Global test 100%: {pack.title}',
            )
            GlobalTestAttempt.objects.filter(pk=attempt.pk).update(coins_awarded=True)
            coins_earned = pack.coin_reward

    return JsonResponse({
        'success':      True,
        'score':        score,
        'total':        total,
        'coins_earned': coins_earned,
        'attempt_id':   attempt.pk,
    })


@login_required
def global_test_results(request, pk, attempt_pk):
    pack    = get_object_or_404(TestPack, pk=pk)
    user    = request.user
    attempt = get_object_or_404(GlobalTestAttempt, pk=attempt_pk, student=user)

    answer_map = {a.question_id: a for a in attempt.answers.select_related('choice', 'question')}
    question_results = []
    for q in pack.questions.prefetch_related('choices').all():
        ans = answer_map.get(q.pk)
        question_results.append({
            'question':      q,
            'answer':        ans,
            'is_correct':    ans.is_correct if ans else False,
            'chosen_choice': ans.choice if ans else None,
        })

    return render(request, 'tests/global_test_results.html', {
        'pack':             pack,
        'attempt':          attempt,
        'question_results': question_results,
    })