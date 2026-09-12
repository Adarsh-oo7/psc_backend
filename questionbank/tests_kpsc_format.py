from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User
from questionbank.kpsc_format import (
    normalize_options, normalize_correct_answer, clean_option_text,
    clean_question_text, is_servable, servability_issues, format_question_payload,
    logical_answer_mismatch, shuffle_options, grade_selected_option, interleave_reviews,
)
from questionbank.models import Question, Topic
from questionbank.engine import QuestionEngine
from questionbank.serializers import QuestionSerializer


class KpscFormatTests(SimpleTestCase):
    def test_normalizes_list_and_lowercase_keys(self):
        opts = normalize_options(['alpha', 'beta', 'gamma', 'delta'])
        self.assertEqual(list(opts.keys()), ['A', 'B', 'C', 'D'])
        self.assertEqual(opts['B'], 'beta')
        self.assertEqual(normalize_options({'a': 'One', 'b': 'Two', 'c': 'Three', 'd': 'Four'})['A'], 'One')

    def test_strips_letter_prefix_but_keeps_match_lists(self):
        self.assertEqual(clean_option_text('A) Bronze'), 'Bronze')
        self.assertEqual(clean_option_text('[b] Alluvial fan'), 'Alluvial fan')
        self.assertEqual(
            clean_option_text('A:3 B:4 C:1 D:2'),
            'A:3 B:4 C:1 D:2',
        )
        self.assertEqual(clean_option_text('Answer: RNA'), 'RNA')

    def test_splits_mashed_questions(self):
        text = 'ശ്രീനാരായണ ഗുരു സമാധിയായ വർഷം ഏത്?31. ശ്രീനാരായണ ഗുരു രമണ മഹർഷിയെ കണ്ടുമുട്ടിയ വർഷം ഏത്?'
        self.assertEqual(clean_question_text(text), 'ശ്രീനാരായണ ഗുരു സമാധിയായ വർഷം ഏത്?')

    def test_drops_extra_ef_keys(self):
        opts = normalize_options({'A': '1925', 'B': '1926', 'C': '1928', 'D': '1930', 'E': '1912', 'F': '1914'})
        self.assertEqual(set(opts.keys()), {'A', 'B', 'C', 'D'})
        self.assertNotIn('E', opts)

    def test_invalid_answer_and_duplicates_are_unservable(self):
        self.assertFalse(is_servable(
            'Who founded Devasamaj?',
            {'A': 'Samaveda', 'B': 'Shiva Narayana Agnihotri', 'C': '1943', 'D': ''},
            'B',
        ))
        issues = servability_issues(
            'How many spokes are in the Ashoka Chakra?',
            {'A': '26', 'B': '28', 'C': '24', 'D': '26'},
            'C',
        )
        self.assertIn('duplicate_options', issues)

    def test_shuffled_english_malayalam_options_are_unservable(self):
        issues = servability_issues(
            'In which year Calcutta became Capital of British India?',
            {'A': '1434', 'B': '1947 ഓഗസ്റ്റ് 15', 'C': '1772', 'D': '1950 ജനുവരി 26'},
            'C',
        )
        self.assertIn('shuffled_language_options', issues)
        self.assertTrue(is_servable(
            'ഗ്രാൻഡ് സ്ലാം കിരീടം നേടുന്ന ആദ്യത്തെ നിഷ്പക്ഷ അത്‌ലറ്റ് ?',
            {'A': 'Novak Djokovic', 'B': 'Don bodge', 'C': 'Aryna sabalenka', 'D': 'Danielle Collins'},
            'C',
        ))
        self.assertIn('shuffled_language_options', servability_issues(
            'അരങ്ങുകാണാത്ത നടൻ’ എന്നത് ആരുടെ ആത്മകഥയാണ്?',
            {'A': 'Leprocy', 'B': 'സർദാർ പട്ടേൽ', 'C': 'തിക്കോടിയൻ', 'D': 'ലൂയി ഫിഷർ'},
            'C',
        ))

    def test_all_of_the_above_is_valid_kpsc_option(self):
        self.assertTrue(is_servable(
            'Which of the following is a capital expenditure?',
            {
                'A': 'Research and Development Project',
                'B': 'Project Generation',
                'C': 'Project Expansion',
                'D': 'All of the above',
            },
            'D',
        ))

    def test_correct_answer_from_option_text(self):
        opts = normalize_options({'A': 'RNA', 'B': 'DNA', 'C': 'Protein', 'D': 'Lipid'})
        self.assertEqual(normalize_correct_answer('RNA', opts), 'A')
        self.assertEqual(normalize_correct_answer('e', opts), '')

    def test_payload_order_is_abcd(self):
        payload = format_question_payload(
            'Q?',
            {'d': 'Four', 'b': 'Two', 'c': 'Three', 'a': 'One'},
            'b',
        )
        self.assertEqual(list(payload['options'].keys()), ['A', 'B', 'C', 'D'])
        self.assertEqual(payload['correct_answer'], 'B')

    def test_who_question_with_year_as_key_is_mismatch(self):
        issues = servability_issues(
            'Who was the first Chief Minister of Kerala?',
            {
                'A': 'E. M. S. Namboodiripad',
                'B': 'Pattom Thanu Pillai',
                'C': '1957',
                'D': 'C. Achutha Menon',
            },
            'C',
        )
        self.assertIn('answer_key_mismatch', issues)
        self.assertTrue(logical_answer_mismatch(
            'Who was the first Chief Minister of Kerala?',
            {
                'A': 'E. M. S. Namboodiripad',
                'B': 'Pattom Thanu Pillai',
                'C': '1957',
                'D': 'C. Achutha Menon',
            },
            'C',
        ))
        self.assertFalse(logical_answer_mismatch(
            'Who was the first Chief Minister of Kerala?',
            {
                'A': 'E. M. S. Namboodiripad',
                'B': 'Pattom Thanu Pillai',
                'C': 'C. Achutha Menon',
                'D': 'K. Karunakaran',
            },
            'A',
        ))

    def test_year_question_with_name_as_key_is_mismatch(self):
        self.assertTrue(logical_answer_mismatch(
            'In which year was Kerala formed?',
            {'A': '1956', 'B': 'Nehru', 'C': '1947', 'D': '1950'},
            'B',
        ))
        self.assertFalse(logical_answer_mismatch(
            'In which year was Kerala formed?',
            {'A': '1947', 'B': '1950', 'C': '1956', 'D': '1960'},
            'C',
        ))

    def test_shuffle_is_stable_and_grades_the_shown_letter(self):
        opts = {'A': 'Periyar', 'B': 'Bharathapuzha', 'C': 'Pamba', 'D': 'Chaliyar'}
        first, letter1 = shuffle_options(opts, 'A', user_id=7, question_id=42, salt=0)
        second, letter2 = shuffle_options(opts, 'A', user_id=7, question_id=42, salt=0)
        self.assertEqual(first, second)
        self.assertEqual(letter1, letter2)
        self.assertEqual(first[letter1], 'Periyar')
        other, other_letter = shuffle_options(opts, 'A', user_id=8, question_id=42, salt=0)
        self.assertEqual(other[other_letter], 'Periyar')
        ok, displayed = grade_selected_option(
            letter1, opts, 'A', user_id=7, question_id=42, salt=0,
        )
        self.assertTrue(ok)
        self.assertEqual(displayed, letter1)
        wrong, _displayed = grade_selected_option(
            'Z', opts, 'A', user_id=7, question_id=42, salt=0,
        )
        self.assertFalse(wrong)
        next_opts, next_letter = shuffle_options(opts, 'A', user_id=7, question_id=42, salt=1)
        self.assertEqual(next_opts[next_letter], 'Periyar')
        shown, displayed_letter = shuffle_options(opts, 'A', user_id=7, question_id=42, salt=0)
        from questionbank.kpsc_format import selected_to_canonical
        self.assertEqual(
            selected_to_canonical(displayed_letter, opts, 'A', user_id=7, question_id=42, salt=0),
            'A',
        )

    def test_all_of_the_above_stays_last_after_shuffle(self):
        opts = {
            'A': 'Research',
            'B': 'Generation',
            'C': 'Expansion',
            'D': 'All of the above',
        }
        shuffled, letter = shuffle_options(opts, 'D', user_id=3, question_id=9, salt=0)
        self.assertEqual(shuffled['D'], 'All of the above')
        self.assertEqual(letter, 'D')

    def test_topics_map_onto_official_paper_sections(self):
        from questionbank.psc_sections import (
            classify_topic, assign_topic_to_exam_section, exam_blueprint,
        )
        self.assertEqual(classify_topic('Simple Arithmetic — Percentages'), 'maths')
        self.assertEqual(classify_topic('Indian Constitution — Preamble'), 'constitution-and-polity')
        self.assertEqual(classify_topic('Kerala Renaissance'), 'facts-about-kerala')
        self.assertEqual(classify_topic('Daily Current Affairs 2026'), 'daily-current-affairs')
        ldc = exam_blueprint(None)['syllabus']
        self.assertEqual(assign_topic_to_exam_section('Physics — Heat', ldc), 'Science')
        self.assertEqual(assign_topic_to_exam_section('Indian History', ldc), 'Facts About India')
        self.assertEqual(assign_topic_to_exam_section('Percentages', ldc), 'Maths')

    def test_review_interleave_puts_misses_later(self):
        mixed = interleave_reviews(['n1', 'n2', 'n3', 'n4'], ['r1', 'r2'])
        self.assertEqual(mixed, ['n1', 'n2', 'r1', 'n3', 'n4', 'r2'])


class KpscQuestionServingTests(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name='Kerala History', slug='kerala-history-kpsc')
        self.user = User.objects.create_user(username='learner', password='pass12345')

    def test_save_normalizes_and_engine_hides_unpublished(self):
        good = Question.objects.create(
            text='Who was the first Chief Minister of Kerala?',
            options={'b': 'E. M. S. Namboodiripad', 'a': 'Pattom Thanu Pillai', 'c': 'C. Achutha Menon', 'd': 'K. Karunakaran'},
            correct_answer='b',
            topic=self.topic,
            status='approved',
            is_public=True,
        )
        good.refresh_from_db()
        self.assertEqual(list(good.options.keys()), ['A', 'B', 'C', 'D'])
        self.assertEqual(good.correct_answer, 'B')

        broken = Question.objects.create(
            text='The Indus people mixed copper and tin to make',
            options={'A': '1599 AD', 'B': 'ബ്രിട്ടീഷുകാർ', 'C': 'Bronze', 'D': '33'},
            correct_answer='C',
            topic=self.topic,
            status='approved',
            is_public=False,
        )
        served_ids = list(QuestionEngine.get_questions_for_user(self.user, {}, limit=20).values_list('id', flat=True))
        self.assertIn(good.id, served_ids)
        self.assertNotIn(broken.id, served_ids)

    def test_serializer_always_returns_abcd(self):
        q = Question.objects.create(
            text='Which river is the longest in Kerala?',
            options={'C': 'Bharathapuzha', 'A': 'Periyar', 'D': 'Pamba', 'B': 'Chaliyar'},
            correct_answer='A',
            topic=self.topic,
            status='approved',
        )
        data = QuestionSerializer(q).data
        self.assertEqual(list(data['options'].keys()), ['A', 'B', 'C', 'D'])
        self.assertEqual(data['options']['A'], 'Periyar')
        self.assertEqual(data['correct_answer'], 'A')

    def test_wrong_answers_are_mixed_back_into_quizzes(self):
        from questionbank.models import UserAnswer
        questions = []
        for i, name in enumerate(['One', 'Two', 'Three', 'Four', 'Five', 'Six']):
            questions.append(Question.objects.create(
                text=f'Who is person {name} in Kerala history books?',
                options={'A': name, 'B': 'Nehru', 'C': 'Gandhi', 'D': 'Patel'},
                correct_answer='A',
                topic=self.topic,
                status='approved',
                is_public=True,
            ))
        UserAnswer.objects.create(
            user=self.user, question=questions[0], selected_option='B', is_correct=False,
        )
        served_ids = list(QuestionEngine.get_questions_for_user(self.user, {}, limit=6).values_list('id', flat=True))
        self.assertIn(questions[0].id, served_ids)
