import os
import unittest
from app import app, init_system
import config


class TestPetConnectPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_system()
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_platform_branding_is_pet_connect(self):
        """Verify the web application name is PET CONNECT on both portals and config."""
        self.assertEqual(config.PLATFORM_NAME, "PET CONNECT")

        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        html_home = res_home.get_data(as_text=True)
        self.assertIn("PET CONNECT", html_home)
        self.assertNotIn("Anagha Haven", html_home)
        self.assertIn('href="/dev"', html_home)
        self.assertNotIn("Open Shelter Operations Console (Staff Send)", html_home)

        res_dev = self.client.get('/dev')
        self.assertEqual(res_dev.status_code, 200)
        html_dev = res_dev.get_data(as_text=True)
        self.assertIn("PET CONNECT", html_dev)
        self.assertNotIn("Anagha Haven", html_dev)

    def test_02_upfront_customer_email_registration(self):
        """Verify customers can register their email beforehand and retrieve their session."""
        # Reject invalid email
        bad_res = self.client.post('/api/register-email', json={
            'email': 'not-an-email',
            'name': 'Alex Rivera'
        })
        self.assertEqual(bad_res.status_code, 400)
        self.assertFalse(bad_res.get_json()['success'])

        # Accept valid email beforehand
        good_res = self.client.post('/api/register-email', json={
            'email': 'alex.rivera@example.com',
            'name': 'Alex Rivera',
            'phone': '(555) 234-5678'
        })
        self.assertEqual(good_res.status_code, 200)
        data = good_res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['adopter']['email'], 'alex.rivera@example.com')
        self.assertEqual(data['adopter']['name'], 'Alex Rivera')
        self.assertEqual(data['platform'], 'PET CONNECT')

        # Retrieve registered email
        get_res = self.client.get('/api/register-email?email=alex.rivera@example.com')
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.get_json()
        self.assertTrue(get_data['registered'])
        self.assertEqual(get_data['adopter']['name'], 'Alex Rivera')

    def test_03_adoption_request_sends_confirmation_email(self):
        """Verify submitting an adoption request dispatches and archives a PET CONNECT confirmation email."""
        animals_res = self.client.get('/api/animals')
        animals = animals_res.get_json()
        self.assertTrue(len(animals) > 0)
        sample_pet = animals[0]

        req_payload = {
            'pet_id': sample_pet['id'],
            'rfid_tag': sample_pet['rfid_tag'],
            'pet_name': sample_pet['name'],
            'pet_species': sample_pet['species'],
            'pet_breed': sample_pet['breed'],
            'applicant_name': 'Alex Rivera',
            'applicant_email': 'alex.rivera@example.com',
            'applicant_phone': '(555) 234-5678',
            'housing_type': 'House with Fenced Yard',
            'notes': 'Excited to schedule a weekend meet-and-greet!',
            'user_profile': {
                'energy_capacity': 7,
                'maintenance_capacity': 7,
                'space_limit': 8,
                'yard_size': 2,
                'budget_limit': 7,
                'youngest_child_age': 12
            }
        }

        res = self.client.post('/api/adoption-request', json=req_payload)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(body['platform'], 'PET CONNECT')

        confirmation = body['confirmation']
        request_ref = confirmation['request_ref']
        self.assertTrue(request_ref.startswith('PC-'))
        self.assertEqual(confirmation['applicant_email'], 'alex.rivera@example.com')
        self.assertIn('PET CONNECT', confirmation['email_subject'])
        self.assertIn('PET CONNECT', confirmation['email_text'])
        self.assertIn(request_ref, confirmation['email_text'])
        self.assertTrue(len(confirmation['care_checklist']) >= 3)

        # Verify confirmation email HTML view endpoint
        html_res = self.client.get(f'/api/adoption-request/{request_ref}/email?format=html')
        self.assertEqual(html_res.status_code, 200)
        html_email = html_res.get_data(as_text=True)
        self.assertIn('PET CONNECT', html_email)
        self.assertIn(request_ref, html_email)

        # Verify confirmation email EML download endpoint
        eml_res = self.client.get(f'/api/adoption-request/{request_ref}/email?format=eml')
        self.assertEqual(eml_res.status_code, 200)

        # Verify resend confirmation email endpoint
        resend_res = self.client.post(f'/api/adoption-request/{request_ref}/resend', json={
            'email': 'alex.rivera@example.com'
        })
        self.assertEqual(resend_res.status_code, 200)
        self.assertTrue(resend_res.get_json()['success'])

        # Verify staff adoption requests list includes this request
        list_res = self.client.get('/api/adoption-requests')
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.get_json()
        refs = [r['request_ref'] for r in list_data['requests']]
        self.assertIn(request_ref, refs)

    def test_04_matcher_upgrades_and_predict_stay(self):
        """Verify upgraded matcher returns compatibility_tier and care_checklist, and /api/predict-stay works."""
        match_res = self.client.post('/api/match', json={
            'user_profile': {
                'energy_capacity': 6,
                'maintenance_capacity': 6,
                'space_limit': 6,
                'yard_size': 1,
                'budget_limit': 6,
                'youngest_child_age': 10
            },
            'species_filter': 'all'
        })
        self.assertEqual(match_res.status_code, 200)
        match_data = match_res.get_json()
        self.assertTrue(len(match_data['matches']) > 0)
        first_match = match_data['matches'][0]['match_analysis']
        self.assertIn('compatibility_tier', first_match)
        self.assertIn('care_checklist', first_match)
        self.assertTrue(len(first_match['care_checklist']) >= 3)

        predict_res = self.client.post('/api/predict-stay', json={
            'species': 'Dog',
            'breed': 'Golden Retriever',
            'age_months': 24,
            'size': 'Large',
            'energy_level': 6
        })
        self.assertEqual(predict_res.status_code, 200)
        pred_data = predict_res.get_json()
        self.assertTrue(pred_data['success'])
        self.assertIn('prediction', pred_data)

    def test_05_shelter_staff_console_auto_fill_and_send(self):
        """Verify Shelter Operations Console auto-fills customer request info and staff can dispatch the confirmation email."""
        list_res = self.client.get('/api/adoption-requests')
        self.assertEqual(list_res.status_code, 200)
        reqs = list_res.get_json()['requests']
        self.assertTrue(len(reqs) > 0)

        target_req = reqs[0]
        ref = target_req['request_ref']
        # Verify all pre-filled fields needed by the Shelter Operations Console composer are present
        self.assertTrue(target_req.get('applicant_email'))
        self.assertTrue(target_req.get('applicant_name'))
        self.assertTrue(target_req.get('email_subject'))
        self.assertTrue(target_req.get('email_body_text'))
        self.assertTrue(target_req.get('email_body_html'))

        # Verify shelter employee can dispatch/approve with a custom coordinator note
        staff_res = self.client.post(f'/api/adoption-request/{ref}/staff-send', json={
            'to_email': target_req['applicant_email'],
            'to_name': target_req['applicant_name'],
            'subject': target_req['email_subject'],
            'body_text': target_req['email_body_text'],
            'staff_note': 'Hi! Your meet-and-greet is confirmed for Saturday at 2:00 PM.',
            'dispatch_channel': 'GMAIL_WEB'
        })
        self.assertEqual(staff_res.status_code, 200)
        staff_data = staff_res.get_json()
        self.assertTrue(staff_data['success'])
        self.assertEqual(staff_data['reference_id'], ref)
        self.assertIn('Saturday at 2:00 PM', staff_data['body_text'])
        self.assertIn('STAFF', staff_data['delivery_status'])


if __name__ == '__main__':
    unittest.main()

