import importlib
import unittest
from unittest.mock import patch


class AppEntrypointTests(unittest.TestCase):
    def test_main_calls_uvicorn(self):
        app_module = importlib.import_module("app")

        with patch("uvicorn.run") as mock_run:
            app_module.main()

        mock_run.assert_called_once_with(
            "app:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
        )


if __name__ == "__main__":
    unittest.main()
