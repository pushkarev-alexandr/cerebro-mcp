import unittest
from unittest.mock import Mock, call, patch

import server


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_session_takes_priority(self):
        for credentials in ({}, {"CEREBRO_USER": "user", "CEREBRO_PASSWORD": "password"}):
            with self.subTest(credentials_present=bool(credentials)):
                db = Mock(CLIENT_CONNECTED=0)
                db.connect_from_cerebro_client.return_value = 0
                with patch.object(server.database, "Database", return_value=db), patch.dict(
                    server.os.environ, credentials, clear=True
                ):
                    async with server.app_lifespan(None) as state:
                        self.assertIs(state["db"], db)
                        db.connect.assert_not_called()
                    db.disconnect.assert_called_once_with()

    async def test_credentials_used_when_client_unavailable(self):
        for status in (1, 2):
            with self.subTest(status=status):
                db = Mock(CLIENT_CONNECTED=0)
                db.connect_from_cerebro_client.return_value = status
                with patch.object(server.database, "Database", return_value=db), patch.dict(
                    server.os.environ,
                    {"CEREBRO_USER": "user", "CEREBRO_PASSWORD": "password"},
                    clear=True,
                ):
                    async with server.app_lifespan(None) as state:
                        self.assertIs(state["db"], db)
                    self.assertEqual(db.mock_calls, [
                        call.connect_from_cerebro_client(),
                        call.connect("user", "password"),
                        call.disconnect(),
                    ])

    async def test_missing_fallback_credentials(self):
        for credentials in ({}, {"CEREBRO_USER": "user"}, {"CEREBRO_PASSWORD": "password"}):
            with self.subTest(fields=list(credentials)):
                db = Mock(CLIENT_CONNECTED=0)
                db.connect_from_cerebro_client.return_value = 2
                with patch.object(server.database, "Database", return_value=db), patch.dict(
                    server.os.environ, credentials, clear=True
                ):
                    with self.assertRaisesRegex(RuntimeError, "Open Cerebro and sign in"):
                        async with server.app_lifespan(None):
                            self.fail("Startup must fail without authentication")
                    db.connect.assert_not_called()
                    db.disconnect.assert_called_once_with()

    async def test_failed_password_login_is_propagated_and_cleaned_up(self):
        db = Mock(CLIENT_CONNECTED=0)
        db.connect_from_cerebro_client.return_value = 2
        db.connect.side_effect = RuntimeError("Authentication failed")
        with patch.object(server.database, "Database", return_value=db), patch.dict(
            server.os.environ,
            {"CEREBRO_USER": "user", "CEREBRO_PASSWORD": "password"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "Authentication failed"):
                async with server.app_lifespan(None):
                    self.fail("Startup must fail when authentication fails")
            db.disconnect.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
