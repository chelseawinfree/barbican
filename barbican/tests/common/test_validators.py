# Copyright (c) 2013-2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import unittest

import testtools

from barbican.common import exception as excep
from barbican.common import validators
from barbican.tests import utils

VALID_PKCS10 = "valid PKCS10"
VALID_EXTENSIONS = "valid extensions"
VALID_FULL_CMC = "valid CMC"


def suite():
    suite = unittest.TestSuite()

    suite.addTest(WhenTestingSecretValidator())

    return suite


class WhenTestingValidatorsFunctions(utils.BaseTestCase):

    def test_secret_too_big_is_false_for_small_secrets(self):
        data = b'\xb0'

        is_too_big = validators.secret_too_big(data)

        self.assertFalse(is_too_big)

    def test_secret_too_big_is_true_for_big_secrets(self):
        data = b'\x01' * validators.CONF.max_allowed_secret_in_bytes
        data += b'\x01'

        is_too_big = validators.secret_too_big(data)

        self.assertTrue(is_too_big)

    def test_secret_too_big_is_true_for_big_unicode_secrets(self):
        beer = u'\U0001F37A'
        data = beer * (validators.CONF.max_allowed_secret_in_bytes / 4)
        data += u'1'

        is_too_big = validators.secret_too_big(data)

        self.assertTrue(is_too_big)


class WhenTestingSecretValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingSecretValidator, self).setUp()

        self.name = 'name'
        self.payload = b'not-encrypted'
        self.payload_content_type = 'text/plain'
        self.secret_algorithm = 'algo'
        self.secret_bit_length = 512
        self.secret_mode = 'cytype'

        self.secret_req = {'name': self.name,
                           'payload_content_type': self.payload_content_type,
                           'algorithm': self.secret_algorithm,
                           'bit_length': self.secret_bit_length,
                           'mode': self.secret_mode,
                           'payload': self.payload}

        self.validator = validators.NewSecretValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.secret_req)

    def test_should_validate_no_name(self):
        del self.secret_req['name']
        self.validator.validate(self.secret_req)

    def test_should_validate_empty_name(self):
        self.secret_req['name'] = '    '
        self.validator.validate(self.secret_req)

    def test_should_validate_no_payload(self):
        del self.secret_req['payload']
        del self.secret_req['payload_content_type']
        result = self.validator.validate(self.secret_req)

        self.assertFalse('payload' in result)

    def test_should_validate_payload_with_whitespace(self):
        self.secret_req['payload'] = '  ' + self.payload + '    '
        result = self.validator.validate(self.secret_req)

        self.assertEqual(self.payload, result['payload'])

    def test_should_validate_future_expiration(self):
        self.secret_req['expiration'] = '2114-02-28T19:14:44.180394'
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))

    def test_should_validate_future_expiration_no_t(self):
        self.secret_req['expiration'] = '2114-02-28 19:14:44.180394'
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))

    def test_should_validate_expiration_with_z(self):
        expiration = '2114-02-28 19:14:44.180394Z'
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        self.assertEqual(expiration[:-1], str(result['expiration']))

    def test_should_validate_expiration_with_tz(self):
        expiration = '2114-02-28 12:14:44.180394-05:00'
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        expected = expiration[:-6].replace('12', '17', 1)
        self.assertEqual(expected, str(result['expiration']))

    def test_should_validate_expiration_extra_whitespace(self):
        expiration = '2114-02-28 12:14:44.180394-05:00      '
        self.secret_req['expiration'] = expiration
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(isinstance(result['expiration'], datetime.datetime))
        expected = expiration[:-12].replace('12', '17', 1)
        self.assertEqual(expected, str(result['expiration']))

    def test_should_validate_empty_expiration(self):
        self.secret_req['expiration'] = '  '
        result = self.validator.validate(self.secret_req)

        self.assertTrue('expiration' in result)
        self.assertTrue(not result['expiration'])

    def test_should_raise_numeric_name(self):
        self.secret_req['name'] = 123

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('name', exception.invalid_property)

    def test_should_raise_negative_bit_length(self):
        self.secret_req['bit_length'] = -23

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('bit_length', exception.invalid_property)

    def test_should_raise_non_integer_bit_length(self):
        self.secret_req['bit_length'] = "23"

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('bit_length', exception.invalid_property)

    def test_validation_should_raise_with_empty_payload(self):
        self.secret_req['payload'] = '   '

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('payload', exception.invalid_property)

    def test_should_raise_already_expired(self):
        self.secret_req['expiration'] = '2004-02-28T19:14:44.180394'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('expiration', exception.invalid_property)

    def test_should_raise_expiration_nonsense(self):
        self.secret_req['expiration'] = 'nonsense'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )
        self.assertEqual('expiration', exception.invalid_property)

    def test_should_raise_all_nulls(self):
        self.secret_req = {'name': None,
                           'algorithm': None,
                           'bit_length': None,
                           'mode': None}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_all_empties(self):
        self.secret_req = {'name': '',
                           'algorithm': '',
                           'bit_length': '',
                           'mode': ''}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_no_payload_content_type(self):
        del self.secret_req['payload_content_type']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_with_message_w_bad_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'plain/text'

        try:
            self.validator.validate(self.secret_req)
        except excep.InvalidObject as e:
            self.assertNotEqual(str(e), 'None')
            self.assertIsNotNone(e.message)
            self.assertNotEqual(e.message, 'None')
        else:
            self.fail('No validation exception was raised')

    def test_should_validate_mixed_case_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TeXT/PlaiN'
        self.validator.validate(self.secret_req)

    def test_should_validate_upper_case_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TEXT/PLAIN'
        self.validator.validate(self.secret_req)

    def test_should_raise_with_mixed_case_wrong_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TeXT/PlaneS'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_with_upper_case_wrong_payload_content_type(self):
        self.secret_req['payload_content_type'] = 'TEXT/PLANE'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_with_plain_text_and_encoding(self):
        self.secret_req['payload_content_encoding'] = 'base64'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_raise_with_wrong_encoding(self):
        self.secret_req['payload_content_type'] = 'application/octet-stream'
        self.secret_req['payload_content_encoding'] = 'unsupported'

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.secret_req,
        )

    def test_should_validate_with_wrong_encoding(self):
        self.secret_req['payload_content_type'] = 'application/octet-stream'
        self.secret_req['payload_content_encoding'] = 'base64'

        self.validator.validate(self.secret_req)


class WhenTestingContainerValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingContainerValidator, self).setUp()

        self.name = 'name'
        self.type = 'generic'
        self.secret_refs = [
            {
                'name': 'testname',
                'secret_ref': '1231'
            },
            {
                'name': 'testname2',
                'secret_ref': '1232'
            }
        ]

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

        self.validator = validators.ContainerValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.container_req)

    def test_should_validate_no_name(self):
        del self.container_req['name']
        self.validator.validate(self.container_req)

    def test_should_validate_empty_name(self):
        self.container_req['name'] = '    '
        self.validator.validate(self.container_req)

    def test_should_raise_no_type(self):
        del self.container_req['type']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        # TODO(hgedikli): figure out why invalid_property is null here
        # self.assertEqual('type', e.exception.invalid_property)

    def test_should_raise_empty_type(self):
        self.container_req['type'] = ''

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('type', exception.invalid_property)

    def test_should_raise_not_supported_type(self):
        self.container_req['type'] = 'testtype'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('type', exception.invalid_property)

    def test_should_raise_numeric_name(self):
        self.container_req['name'] = 123

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('name', exception.invalid_property)

    def test_should_raise_all_nulls(self):
        self.container_req = {'name': None,
                              'type': None,
                              'bit_length': None,
                              'secret_refs': None}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_raise_all_empties(self):
        self.container_req = {'name': '',
                              'type': '',
                              'secret_refs': []}

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_validate_empty_secret_refs(self):
        self.container_req['secret_refs'] = []
        self.validator.validate(self.container_req)

    def test_should_raise_no_secret_ref_in_secret_refs(self):
        del self.container_req['secret_refs'][0]['secret_ref']

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_raise_empty_secret_ref_in_secret_refs(self):
        self.container_req['secret_refs'][0]['secret_ref'] = ''

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_raise_numeric_secret_ref_in_secret_refs(self):
        self.container_req['secret_refs'][0]['secret_ref'] = 123

        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

    def test_should_raise_duplicate_names_in_secret_refs(self):
        self.container_req['secret_refs'].append(
            self.container_req['secret_refs'][0])

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_duplicate_secret_ids_in_secret_refs(self):

        secret_ref = self.container_req['secret_refs'][0]
        secret_ref['name'] = 'testname3'
        self.container_req['secret_refs'].append(secret_ref)

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_duplicate_secret_ref_format_ids_in_secret_refs(self):
        """Test duplicate secret_id presence as part of single container.

           Here secret_id is represented in different format and secret_id is
           extracted from there.
        """

        secret_refs = [
            {
                'name': 'testname',
                'secret_ref': 'http://localhost:9311/v1/12345/secrets/1231'
            },
            {
                'name': 'testname2',
                'secret_ref': 'http://localhost:9311/v1/12345/secrets//1232'
            },
            {
                'name': 'testname3',
                'secret_ref': 'http://localhost:9311/v1/12345/secrets//1231/'

            }
        ]

        container_req = {'name': 'name',
                         'type': 'generic',
                         'secret_refs': secret_refs}

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)


class WhenTestingRSAContainerValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingRSAContainerValidator, self).setUp()

        self.name = 'name'
        self.type = 'rsa'
        self.secret_refs = [
            {
                'name': 'public_key',
                'secret_ref': '1231'
            },
            {
                'name': 'private_key',
                'secret_ref': '1232'
            },
            {
                'name': 'private_key_passphrase',
                'secret_ref': '1233'
            }
        ]

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

        self.validator = validators.ContainerValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.container_req)

    def test_should_raise_no_names_in_secret_refs(self):
        del self.container_req['secret_refs'][0]['name']

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_empty_names_in_secret_refs(self):
        self.container_req['secret_refs'][0]['name'] = ''

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_unsupported_names_in_secret_refs(self):
        self.container_req['secret_refs'][0]['name'] = 'testttt'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_duplicate_secret_id_in_secret_refs(self):
        self.container_req['secret_refs'][0]['secret_ref'] = (
            self.container_req['secret_refs'][2]['secret_ref'])

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_more_than_3_secret_refs(self):
        new_secret_ref = {
            'name': 'new secret ref',
            'secret_ref': '234234'
        }
        self.container_req['secret_refs'].append(new_secret_ref)

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req,
        )

        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_if_required_name_missing(self):
        name = 'name'
        type = 'certificate'
        secret_refs = [
            {
                'name': 'private_key',
                'secret_ref': '123'
            },
            {
                'name': 'private_key_passphrase',
                'secret_ref': '123'
            }
        ]
        container_req = {'name': name, 'type': type,
                         'secret_refs': secret_refs}
        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            container_req)
        self.assertEqual('secret_refs', exception.invalid_property)


class WhenTestingCertificateContainerValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingCertificateContainerValidator, self).setUp()

        self.name = 'name'
        self.type = 'certificate'
        self.secret_refs = [
            {
                'name': 'certificate',
                'secret_ref': 'S4dfsdrf'
            },
            {
                'name': 'private_key',
                'secret_ref': '1231'
            },
            {
                'name': 'private_key_passphrase',
                'secret_ref': '1232'
            },
            {
                'name': 'intermediates',
                'secret_ref': '1233'
            }
        ]

        self.container_req = {'name': self.name,
                              'type': self.type,
                              'secret_refs': self.secret_refs}

        self.validator = validators.ContainerValidator()

    def test_should_validate_all_fields(self):
        self.validator.validate(self.container_req)

    def test_should_raise_more_than_4_secret_refs(self):
        new_secret_ref = {
            'name': 'new secret ref',
            'secret_ref': '234234'
        }
        self.container_req['secret_refs'].append(new_secret_ref)

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req)
        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_unsupported_names_in_secret_refs(self):
        self.container_req['secret_refs'][0]['name'] = 'public_key'

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.container_req)
        self.assertEqual('secret_refs', exception.invalid_property)

    def test_should_raise_if_required_name_missing(self):
        name = 'name'
        type = 'certificate'
        secret_refs = [
            {
                'name': 'private_key',
                'secret_ref': '123'
            },
            {
                'name': 'intermediates',
                'secret_ref': '123'
            }
        ]
        container_req = {'name': name, 'type': type,
                         'secret_refs': secret_refs}
        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            container_req)
        self.assertEqual('secret_refs', exception.invalid_property)


class WhenTestingTransportKeyValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingTransportKeyValidator, self).setUp()

        self.plugin_name = 'name'
        self.transport_key = 'abcdef'
        self.transport_req = {'plugin_name': self.plugin_name,
                              'transport_key': self.transport_key}

        self.validator = validators.NewTransportKeyValidator()

    def test_should_raise_with_invalid_json_data_type(self):
        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            []
        )

    def test_should_raise_with_empty_transport_key(self):
        self.transport_req['transport_key'] = ''

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            self.transport_req
        )

        self.assertEqual('transport_key', exception.invalid_property)


class WhenTestingConsumerValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingConsumerValidator, self).setUp()

        self.name = 'name'
        self.URL = 'http://my.url/resource/UUID'
        self.consumer_req = {'name': self.name,
                             'URL': self.URL}
        self.validator = validators.ContainerConsumerValidator()

    def test_should_raise_with_invalid_json_data_type(self):
        self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            []
        )

    def test_should_raise_with_missing_name(self):
        consumer_req = {'URL': self.URL}
        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            consumer_req
        )

        self.assertIn('\'name\'', exception.args[0])

    def test_should_raise_with_missing_URL(self):
        consumer_req = {'name': self.name}

        exception = self.assertRaises(
            excep.InvalidObject,
            self.validator.validate,
            consumer_req
        )

        self.assertIn('\'URL\'', exception.args[0])

    def test_should_validate_all_fields(self):
        self.validator.validate(self.consumer_req)


class WhenTestingKeyTypeOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingKeyTypeOrderValidator, self).setUp()
        self.type = 'key'
        self.meta = {"name": "secretname",
                     "algorithm": "AES",
                     "bit_length": 256,
                     "mode": "cbc",
                     'payload_content_type':
                     'application/octet-stream'}

        self.key_order_req = {'type': self.type,
                              'meta': self.meta}

        self.validator = validators.TypeOrderValidator()

    def test_should_pass_with_certificate_type_in_order_refs(self):
        self.key_order_req['type'] = 'certificate'
        result = self.validator.validate(self.key_order_req)
        self.assertEqual('certificate', result['type'])

    def test_should_pass_good_bit_meta_in_order_refs(self):
        self.key_order_req['meta']['algorithm'] = 'AES'
        self.key_order_req['meta']['bit_length'] = 256
        result = self.validator.validate(self.key_order_req)
        self.assertTrue(result['meta']['expiration'] is None)

    def test_should_pass_good_exp_meta_in_order_refs(self):
        self.key_order_req['meta']['algorithm'] = 'AES'
        ony_year_factor = datetime.timedelta(days=1 * 365)
        date_after_year = datetime.datetime.now() + ony_year_factor
        date_after_year_str = date_after_year.strftime('%Y-%m-%d %H:%M:%S')
        self.key_order_req['meta']['expiration'] = date_after_year_str
        result = self.validator.validate(self.key_order_req)

        self.assertTrue('expiration' in result['meta'])
        self.assertTrue(isinstance(result['meta']['expiration'],
                                   datetime.datetime))

    def test_should_raise_with_no_type_in_order_refs(self):
        del self.key_order_req['type']

        exception = self.assertRaises(excep.InvalidObject,
                                      self.validator.validate,
                                      self.key_order_req)
        self.assertEqual('type', exception.invalid_property)

    def test_should_raise_with_bad_type_in_order_refs(self):
        self.key_order_req['type'] = 'badType'

        exception = self.assertRaises(excep.InvalidObject,
                                      self.validator.validate,
                                      self.key_order_req)
        self.assertEqual('type', exception.invalid_property)

    def test_should_raise_with_no_meta_in_order_refs(self):
        del self.key_order_req['meta']

        exception = self.assertRaises(excep.InvalidObject,
                                      self.validator.validate,
                                      self.key_order_req)
        self.assertEqual('meta', exception.invalid_property)

    def test_should_raise_with_wrong_exp_meta_in_order_refs(self):
        self.key_order_req['meta']['algorithm'] = 'AES'
        self.key_order_req['meta']['expiration'] = '2014-02-28T19:14:44.180394'

        exception = self.assertRaises(excep.InvalidObject,
                                      self.validator.validate,
                                      self.key_order_req)
        self.assertEqual('expiration', exception.invalid_property)

    @testtools.skip("due to bug#1365131")
    def test_should_not_raise_correct_hmac_order_refs(self):
        self.key_order_req['meta']['algorithm'] = 'hmacsha1'
        del self.key_order_req['meta']['mode']

        result = self.validator.validate(self.key_order_req)
        self.assertTrue(result is not None)
        self.assertTrue(result['meta']['algorithm'] == 'hmacsha1')


class WhenTestingAsymmetricTypeOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingAsymmetricTypeOrderValidator, self).setUp()
        self.type = 'asymmetric'
        self.meta = {"name": "secretname",
                     "algorithm": "RSA",
                     "bit_length": 256,
                     'payload_content_type':
                     'application/octet-stream'}

        self.asymmetric_order_req = {'type': self.type,
                                     'meta': self.meta}

        self.validator = validators.TypeOrderValidator()

    def test_should_pass_good_meta_in_order_refs(self):
        result = self.validator.validate(self.asymmetric_order_req)
        self.assertIsNone(result['meta']['expiration'])

    def test_should_raise_with_no_algorithm_in_order_refs(self):
        del self.asymmetric_order_req['meta']['algorithm']

        self.assertRaises(excep.InvalidObject,
                          self.validator.validate,
                          self.asymmetric_order_req)

    def test_should_raise_with_wrong_payload_content_type_in_order_refs(self):
        # NOTE(jaosorior): this is actually a valid content type, but it is not
        # supported by asymmetric key orders.
        self.asymmetric_order_req['meta']['payload_content_type'] = (
            'text/plain')
        self.assertRaises(excep.UnsupportedField,
                          self.validator.validate,
                          self.asymmetric_order_req)

    def test_should_pass_with_wrong_algorithm_in_asymmetric_order_refs(self):
        # Note (atiwari): because validator should not check
        # algorithm but that should checked at crypto_plugin
        # supports method.
        self.asymmetric_order_req['meta']['algorithm'] = 'aes'
        result = self.validator.validate(self.asymmetric_order_req)
        self.assertIsNone(result['meta']['expiration'])


class WhenTestingSimpleCMCOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingSimpleCMCOrderValidator, self).setUp()
        self.type = 'certificate'
        self.meta = {'request_type': 'simple-cmc',
                     'request_data': VALID_PKCS10,
                     'requestor_name': 'Barbican User',
                     'requestor_email': 'barbican_user@example.com',
                     'requestor_phone': '555-1212'}
        self._set_order()
        self.validator = validators.TypeOrderValidator()

    def _set_order(self):
        self.order_req = {'type': self.type,
                          'meta': self.meta}

    def test_should_pass_good_data(self):
        self.validator.validate(self.order_req)

    def test_should_raise_with_no_metadata(self):
        self.order_req = {'type': self.type}
        self.assertRaises(excep.InvalidObject,
                          self.validator.validate,
                          self.order_req)

    def test_should_raise_with_bad_request_type(self):
        self.meta['request_type'] = 'bad_request_type'
        self._set_order()
        self.assertRaises(excep.InvalidCertificateRequestType,
                          self.validator.validate,
                          self.order_req)

    def test_should_raise_with_no_request_data(self):
        del self.meta['request_data']
        self._set_order()
        self.assertRaises(excep.MissingMetadataField,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_bad_pkcs10_data(self):
        self.meta['request_data'] = 'Bad PKCS#10 Data'
        self._set_order()
        self.assertRaises(excep.InvalidPKCS10Data,
                          self.validator.validate,
                          self.order_req)


class WhenTestingFullCMCOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingFullCMCOrderValidator, self).setUp()
        self.type = 'certificate'
        self.meta = {'request_type': 'full-cmc',
                     'request_data': VALID_FULL_CMC,
                     'requestor_name': 'Barbican User',
                     'requestor_email': 'barbican_user@example.com',
                     'requestor_phone': '555-1212'}
        self._set_order()
        self.validator = validators.TypeOrderValidator()

    def _set_order(self):
        self.order_req = {'type': self.type,
                          'meta': self.meta}

    def test_should_pass_good_data(self):
        self.validator.validate(self.order_req)

    def test_should_raise_with_no_request_data(self):
        del self.meta['request_data']
        self._set_order()
        self.assertRaises(excep.MissingMetadataField,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_bad_cmc_data(self):
        self.meta['request_data'] = 'Bad CMC Data'
        self._set_order()
        self.assertRaises(excep.InvalidCMCData,
                          self.validator.validate,
                          self.order_req)


class WhenTestingCustomOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingCustomOrderValidator, self).setUp()
        self.type = 'certificate'
        self.meta = {'request_type': 'custom',
                     'ca_param_1': 'value_1',
                     'ca_param_2': 'value_2',
                     'requestor_name': 'Barbican User',
                     'requestor_email': 'barbican_user@example.com',
                     'requestor_phone': '555-1212'}
        self._set_order()
        self.validator = validators.TypeOrderValidator()

    def _set_order(self):
        self.order_req = {'type': self.type,
                          'meta': self.meta}

    def test_should_pass_good_data(self):
        self.validator.validate(self.order_req)

    def test_should_pass_with_no_request_type(self):
        # defaults to custom
        del self.meta['request_type']
        self._set_order()
        self.validator.validate(self.order_req)


class WhenTestingStoredKeyOrderValidator(utils.BaseTestCase):

    def setUp(self):
        super(WhenTestingStoredKeyOrderValidator, self).setUp()
        self.type = 'certificate'
        self.meta = {'request_type': 'stored-key',
                     'container_ref': 'good_container_ref',
                     'subject_dn': 'cn=barbican-server,o=example.com',
                     'extensions': VALID_EXTENSIONS,
                     'requestor_name': 'Barbican User',
                     'requestor_email': 'barbican_user@example.com',
                     'requestor_phone': '555-1212'}
        self.order_req = {'type': self.type,
                          'meta': self.meta}
        self.validator = validators.TypeOrderValidator()

    def test_should_pass_good_data(self):
        self.validator.validate(self.order_req)

    def test_should_raise_with_no_container_ref(self):
        del self.meta['container_ref']
        self.assertRaises(excep.MissingMetadataField,
                          self.validator.validate,
                          self.order_req)

    def test_should_raise_with_no_subject_dn(self):
        del self.meta['subject_dn']
        self.assertRaises(excep.MissingMetadataField,
                          self.validator.validate,
                          self.order_req)

    def test_should_pass_with_no_extensions_data(self):
        del self.meta['extensions']
        self.validator.validate(self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_bad_extensions_data(self):
        self.meta['extensions'] = 'Bad extensions data'
        self.assertRaises(excep.InvalidExtensionsData,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_bad_subject_dn(self):
        self.meta['subject_dn'] = "Bad subject DN data"
        self.assertRaises(excep.InvalidSubjectDN,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_missing_container(self):
        self.meta['container_ref'] = 'missing_container_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_container_not_cert_type(self):
        self.meta['container_ref'] = 'bad_type_container_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_inaccessible_container(self):
        self.meta['container_ref'] = 'inaccessible_container_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_missing_public_key(self):
        self.meta['container_ref'] = 'missing_public_key_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_inaccessible_public_key(self):
        self.meta['container_ref'] = 'inaccessible_public_key_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

    @testtools.skip("Not yet implemented")
    def test_should_raise_with_missing_private_key(self):
        self.meta['container_ref'] = 'missing_private_key_ref'
        self.assertRaises(excep.InvalidContainer,
                          self.validator.validate,
                          self.order_req)

if __name__ == '__main__':
    unittest.main()
