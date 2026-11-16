import inspect
import json
import unittest
from unittest.mock import Mock

from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import Context

import server


class MCPCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_keep_their_public_schema_and_annotations(self):
        tools = await server.mcp.list_tools()
        expected_names = {
            name for name, value in vars(server).items()
            if name.startswith("cerebro_") and inspect.iscoroutinefunction(value)
        }
        self.assertTrue(expected_names)
        self.assertEqual({tool.name for tool in tools}, expected_names)
        for tool in tools:
            with self.subTest(tool=tool.name):
                wire = tool.model_dump(by_alias=True)
                self.assertEqual(set(wire["inputSchema"]["properties"]), {"params"})
                self.assertTrue(wire["annotations"]["readOnlyHint"])
                self.assertFalse(wire["annotations"]["destructiveHint"])

    async def test_sdk_injects_database_context_and_serializes_result(self):
        db = Mock()
        db.statuses.return_value = []
        context = Context(
            mcp_server=server.mcp,
            request_context=ServerRequestContext(
                session=Mock(),
                lifespan_context={"db": db},
                protocol_version="2025-11-25",
                method="tools/call",
            ),
        )
        result = await server.mcp.call_tool(
            "cerebro_get_statuses", {"params": {}}, context=context
        )
        db.statuses.assert_called_once_with()
        wire = result.model_dump(by_alias=True)
        self.assertFalse(wire.get("isError", False))
        self.assertEqual(json.loads(wire["structuredContent"]["result"]), [])


if __name__ == "__main__":
    unittest.main()
