from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User
from questionbank.kpsc_format import (
    normalize_options, normalize_correct_answer, clean_option_text,
    clean_question_text, is_servable, servability_issues,     format_question_payload,
    logical_answer_mismatch, shuffle_options, grade_selected_option, interleave_reviews,
    repair_known_unrelated_question,
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
        self.assertEqual(
            clean_option_text('Nehru Commission [e] None of these'),
            'Nehru Commission',
        )
        self.assertEqual(
            clean_option_text('615 രൂപ ചെയ്യുന്ന വിധം A = P(1 + R/100)ⁿ = 6615'),
            '615 രൂപ',
        )
        self.assertEqual(
            clean_option_text('Aluminium [Junior Asst. Cashier-2015]'),
            'Aluminium',
        )
        self.assertEqual(clean_option_text('[ML2T–2]'), '[ML2T–2]')

    def test_glued_fifth_option_is_stripped_in_payload(self):
        payload = format_question_payload(
            'In 1927, the British Government appointed the Indian Statutory Commission also known as',
            {
                'A': 'Simon Commission',
                'B': 'Mountbatten Commission',
                'C': 'Sedition Committee',
                'D': 'Nehru Commission [e] None of these',
            },
            'A',
        )
        self.assertEqual(payload['options']['D'], 'Nehru Commission')
        self.assertTrue(is_servable(payload['text'], payload['options'], payload['correct_answer']))

    def test_aruna_asaf_ali_mixed_leftovers_are_repaired(self):
        stem = 'During the freedom struggle, Aruna Asaf Ali was a major woman organizer of underground activity in?'
        broken = {
            'A': 'The Pottery',
            'B': 'Rajasthan',
            'C': 'Quit India Movement',
            'D': 'Moradabad',
        }
        self.assertIn('unrelated_options', servability_issues(stem, broken, 'C'))

        class FakeQuestion:
            text = stem
            options = broken
            correct_answer = 'C'
            explanation = ''
            is_public = True

        question = FakeQuestion()
        self.assertTrue(repair_known_unrelated_question(question))
        self.assertEqual(question.options['C'], 'Quit India Movement')
        self.assertEqual(question.correct_answer, 'C')
        self.assertNotIn('Pottery', question.options.values())
        self.assertTrue(is_servable(question.text, question.options, question.correct_answer))

    def test_alexander_tutor_leftovers_are_repaired(self):
        stem = 'Who was the tutor of Alexander the Great ?'
        broken = {
            'A': 'The Pottery',
            'B': 'Aristotle',
            'C': 'Mystical insight by modern seers',
            'D': 'Fairly egalitarian',
        }
        self.assertIn('unrelated_options', servability_issues(stem, broken, 'B'))

        class FakeQuestion:
            text = stem
            options = broken
            correct_answer = 'B'
            explanation = ''
            is_public = True

        question = FakeQuestion()
        self.assertTrue(repair_known_unrelated_question(question))
        self.assertEqual(question.options['B'], 'Aristotle')
        self.assertEqual(set(question.options.values()), {'Plato', 'Aristotle', 'Socrates', 'Pythagoras'})
        self.assertTrue(is_servable(question.text, question.options, question.correct_answer))

    def test_who_wrote_hind_swaraj_is_gandhi_not_book_titles(self):
        class FakeQuestion:
            text = "Who wrote the famous work 'Hind Swaraj'?"
            options = {'A': 'Buffalo', 'B': 'Pulakesin II', 'C': 'Hind Swaraj', 'D': 'Kakatiya'}
            correct_answer = 'C'
            explanation = ''
            is_public = True
        question = FakeQuestion()
        self.assertTrue(repair_known_unrelated_question(question))
        self.assertEqual(question.options['A'], 'Mahatma Gandhi')
        self.assertEqual(question.correct_answer, 'A')
        self.assertNotIn('Hind Swaraj', question.options.values())

    def test_tilak_father_of_unrest_is_repaired(self):
        stem = "Whom the British called 'The father of Indian unrest'"
        broken = {
            'A': 'Dvarasamudhra',
            'B': 'Bal Gangadhar Tilak',
            'C': 'Bhutan',
            'D': 'Pavapuri',
        }
        self.assertIn('unrelated_options', servability_issues(stem, broken, 'B'))
        class FakeQuestion:
            text = stem
            options = broken
            correct_answer = 'B'
            explanation = ''
            is_public = True
        question = FakeQuestion()
        self.assertTrue(repair_known_unrelated_question(question))
        self.assertEqual(question.options['B'], 'Bal Gangadhar Tilak')
        self.assertTrue(is_servable(question.text, question.options, question.correct_answer))

    def test_non_who_history_ivc_leftovers_are_unservable(self):
        issues = servability_issues(
            'Which war was concluded by the Treaty of Salbai(1782)?',
            {
                'A': 'First Anglo-Maratha War',
                'B': 'Kharosthi',
                'C': 'Krakuchanda',
                'D': 'West : Makran Coast of Baluchistan',
            },
            'A',
        )
        self.assertIn('unrelated_options', issues)

    def test_harappan_source_options_stay_servable(self):
        self.assertTrue(is_servable(
            'The Social System of Harappan was',
            {
                'A': 'Fairly egalitarian',
                'B': 'Slave-Labour based',
                'C': 'Colour based',
                'D': 'Caste based',
            },
            'A',
        ))
        self.assertTrue(is_servable(
            'The Indus Valley Civilization has been assigned the period 2500-1800 BC on the basis of',
            {
                'A': 'Mystical insight by modern seers',
                'B': 'Marking on seals',
                'C': 'Radio Carbon dating',
                'D': 'Travellers written accounts',
            },
            'C',
        ))

    def test_article_clause_mixed_with_people_is_unservable(self):
        issues = servability_issues(
            'The only person to become the president of India who had been defeated in a Presidential previous election',
            {
                'A': '51 A(f)',
                'B': 'Lions Club',
                'C': 'Neelam Sanjiva Reddy',
                'D': 'Bhutan and Nepal',
            },
            'C',
        )
        self.assertIn('unrelated_options', issues)

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

    def test_who_appoints_with_unrelated_polity_leftovers_is_unservable(self):
        stem = 'Who appoints the chairman and other members of the Joint Public Service Commission?'
        broken = {
            'A': 'Crossing the floor',
            'B': 'Indirect',
            'C': 'President',
            'D': 'Zail Singh',
        }
        issues = servability_issues(stem, broken, 'C')
        self.assertIn('unrelated_options', issues)
        self.assertFalse(is_servable(stem, broken, 'C'))

        good = {
            'A': 'Prime Minister',
            'B': 'President',
            'C': 'Parliament',
            'D': 'Governor of the concerned States',
        }
        self.assertTrue(is_servable(stem, good, 'B'))
        self.assertTrue(is_servable(
            'Who appoints the RBI Governor?',
            {
                'A': 'President of India',
                'B': 'Prime Minister of India',
                'C': 'Finance Minister of India',
                'D': 'Union Government',
            },
            'D',
        ))
        self.assertTrue(is_servable(
            'The National Security Advisor is appointed by:',
            {
                'A': 'President',
                'B': 'Prime Minister',
                'C': 'Home Minister',
                'D': 'Defence Minister',
            },
            'B',
        ))
        self.assertTrue(is_servable(
            'Who was the first Chief Minister of Kerala?',
            {
                'A': 'E. M. S. Namboodiripad',
                'B': 'Pattom Thanu Pillai',
                'C': 'C. Achutha Menon',
                'D': 'K. Karunakaran',
            },
            'A',
        ))

    def test_antibiotics_question_rejects_physics_leftovers_and_repairs(self):
        stem = 'The drugs used in the treatment & prevention of microbial infections are known as ___'
        broken = {
            'A': 'Antibiotics',
            'B': 'Super conductivity',
            'C': 'absorption of signal in air',
            'D': 'Travirens',
        }
        self.assertIn('unrelated_options', servability_issues(stem, broken, 'A'))
        self.assertFalse(is_servable(stem, broken, 'A'))

        class FakeQuestion:
            text = stem
            options = broken
            correct_answer = 'A'
            explanation = ''
            is_public = True

        question = FakeQuestion()
        self.assertTrue(repair_known_unrelated_question(question))
        self.assertEqual(question.options['A'], 'Antibiotics')
        self.assertEqual(question.options['B'], 'Antiseptics')
        self.assertEqual(question.options['C'], 'Analgesics')
        self.assertEqual(question.options['D'], 'Antipyretics')
        self.assertTrue(is_servable(question.text, question.options, question.correct_answer))

        self.assertTrue(is_servable(
            'Television signal cannot be received generally beyond a particular distance due to',
            {
                'A': 'Curvature of the earth',
                'B': 'Weakness of antenna',
                'C': 'Weakness of signal',
                'D': 'absorption of signal in air',
            },
            'A',
        ))
        self.assertIn('unrelated_options', servability_issues(
            'Gir National Park is situated in',
            {
                'A': 'Vainganga',
                'B': 'Gujarat',
                'C': 'Pulicat Lake',
                'D': 'Antibiotics',
            },
            'B',
        ))
        self.assertTrue(is_servable(
            'Which is a Universal gate?',
            {'A': 'AND', 'B': 'NOR', 'C': 'XOR', 'D': 'NOT'},
            'B',
        ))
        self.assertTrue(is_servable(
            'The students of our school _______ given a challenging task yesterday.',
            {'A': 'were', 'B': 'was', 'C': 'have been', 'D': 'none of these'},
            'A',
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
        lab = [
            {'topic': 'Lab Safety and Instruments', 'marks': 20},
            {'topic': 'Physics', 'marks': 20},
            {'topic': 'Facts About Kerala', 'marks': 10},
        ]
        self.assertEqual(
            assign_topic_to_exam_section('Lab Safety and Instruments', lab),
            'Lab Safety and Instruments',
        )
        self.assertEqual(assign_topic_to_exam_section('Physics', lab), 'Physics')

    def test_subdivision_questions_stay_inside_the_parent_subject(self):
        from questionbank.psc_sections import subdivision_for, summarize_section
        lab = [
            {'topic': 'Chemistry', 'marks': 15},
            {'topic': 'Physics', 'marks': 15},
            {'topic': 'History', 'marks': 10},
        ]
        self.assertEqual(
            subdivision_for('Chemistry — Acids, Bases & Salts', '', 'Chemistry'),
            ('acids-bases-and-salts', 'Acids, Bases and Salts'),
        )
        self.assertEqual(subdivision_for('Chemistry', 'Chemistry', 'Chemistry')[0], 'general')
        groups = [
            (1, 'Chemistry', 'Chemistry', 27),
            (2, 'Chemistry — Acids, Bases & Salts', 'Acids', 4),
            (3, 'Physics — Light, Sound & Optics', 'Physics', 6),
            (4, 'History', 'History', 10),
        ]
        chemistry = summarize_section(groups, 'Chemistry', lab)
        keys = [row['key'] for row in chemistry['subdivisions']]
        self.assertEqual(chemistry['question_count'], 31)
        self.assertIn('acids-bases-and-salts', keys)
        self.assertIn('general', keys)
        self.assertNotIn('light-and-sound', keys)
        physics = summarize_section(groups, 'Physics', lab)
        self.assertEqual(physics['question_count'], 6)
        self.assertEqual(physics['subdivisions'][0]['key'], 'light-and-sound')

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
