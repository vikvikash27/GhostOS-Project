import unittest

from ghostcore.protocol import (
    MAX_MESSAGE_BYTES,
    PROTOCOL_VERSION,
    ProtocolError,
    decode_request,
    encode_message,
    error_response,
    success_response,
)


class ProtocolTests(unittest.TestCase):

    def valid_request(self):
        return {
            "version": PROTOCOL_VERSION,
            "id": "test-001",
            "operation": "health",
            "params": {},
        }

    def test_valid_request_is_decoded(self):
        request = self.valid_request()
        raw = encode_message(request)

        decoded = decode_request(raw)

        self.assertEqual(decoded, request)

    def test_empty_message_is_rejected(self):
        with self.assertRaises(ProtocolError):
            decode_request(b"")

    def test_message_without_newline_is_rejected(self):
        raw = (
            b'{"version":1,"id":"test-001",'
            b'"operation":"health","params":{}}'
        )

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_oversized_message_is_rejected(self):
        raw = b"x" * (MAX_MESSAGE_BYTES + 1)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(ProtocolError):
            decode_request(b"{invalid-json}\n")

    def test_non_object_json_is_rejected(self):
        with self.assertRaises(ProtocolError):
            decode_request(b'["not", "an", "object"]\n')

    def test_missing_request_field_is_rejected(self):
        request = self.valid_request()
        del request["params"]

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_unexpected_request_field_is_rejected(self):
        request = self.valid_request()
        request["uid"] = 0

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_unsupported_protocol_version_is_rejected(self):
        request = self.valid_request()
        request["version"] = 999

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_empty_request_id_is_rejected(self):
        request = self.valid_request()
        request["id"] = ""

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_request_id_over_64_characters_is_rejected(self):
        request = self.valid_request()
        request["id"] = "a" * 65

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_invalid_operation_is_rejected(self):
        request = self.valid_request()
        request["operation"] = 123

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_parameters_must_be_an_object(self):
        request = self.valid_request()
        request["params"] = []

        raw = encode_message(request)

        with self.assertRaises(ProtocolError):
            decode_request(raw)

    def test_encode_message_adds_newline(self):
        message = {"status": "ok"}

        encoded = encode_message(message)

        self.assertTrue(encoded.endswith(b"\n"))

    def test_encode_message_rejects_oversized_message(self):
        message = {"data": "x" * MAX_MESSAGE_BYTES}

        with self.assertRaises(ProtocolError):
            encode_message(message)

    def test_encode_message_rejects_unserializable_data(self):
        message = {"data": object()}

        with self.assertRaises(ProtocolError):
            encode_message(message)

    def test_success_response_structure(self):
        response = success_response(
            "test-001",
            {"status": "healthy"},
        )

        self.assertEqual(response["version"], PROTOCOL_VERSION)
        self.assertEqual(response["id"], "test-001")
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "healthy")

    def test_error_response_structure(self):
        response = error_response(
            "test-001",
            "invalid_request",
        )

        self.assertEqual(response["version"], PROTOCOL_VERSION)
        self.assertEqual(response["id"], "test-001")
        self.assertFalse(response["ok"])
        self.assertEqual(
            response["error"]["code"],
            "invalid_request",
        )


if __name__ == "__main__":
    unittest.main()