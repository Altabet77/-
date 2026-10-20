"""
Samir MCP Server (خادم Model Context Protocol لسمير)

يتيح لبيئة أنتي قرافيتي (Antigravity IDE / CLI) أو أي عميل MCP آخر:
1. استكشاف أدوات سمير وقدراته.
2. استدعاء أدوات سمير للتحكم في جهاز ويندوز، والملفات، وتشغيل التطبيقات، والوسائط.
3. التخاطب البرمجي المباشر مع سمير.
"""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path

# إضافة مسار core_server للـ sys.path
BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core_server"
sys.path.insert(0, str(CORE_DIR))

# إعداد السجل في ملف لتجنب تشويش stdio الخاص بـ JSON-RPC
log_file = CORE_DIR / "data" / "samir_mcp.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("samir_mcp")

# استيراد أدوات سمير
import app.tools.default_tools
import app.tools.windows_agent_tool
import app.tools.browser_media_tool
import app.tools.learning_tool
import app.tools.code_runner_tool
import app.tools.browser_automation_tool
from app.tools.base_tool import tool_registry


async def handle_initialize(params):
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "samir-mcp-server",
            "version": "1.2.0"
        }
    }


async def handle_tools_list(params):
    all_tools = tool_registry.get_all_tool_schemas()
    mcp_tools = []
    for t in all_tools:
        fn = t.get("function", {})
        mcp_tools.append({
            "name": fn.get("name"),
            "description": fn.get("description", ""),
            "inputSchema": fn.get("parameters", {"type": "object", "properties": {}})
        })
    return {"tools": mcp_tools}


async def handle_tools_call(params):
    name = params.get("name")
    args = params.get("arguments", {})
    logger.info(f"MCP Call: {name} with args {args}")

    try:
        result = await tool_registry.execute_tool(name, args, bypass_confirmation=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ]
        }
    except Exception as e:
        logger.error(f"MCP Error in tool {name}: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }
            ],
            "isError": True
        }


async def run_mcp_server():
    logger.info("Samir MCP Server started listening on stdio...")
    loop = asyncio.get_running_loop()

    while True:
        line_str = await loop.run_in_executor(None, sys.stdin.readline)
        if not line_str:
            break

        line_str = line_str.strip()
        if not line_str:
            continue

        try:
            req = json.loads(line_str)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        response = {"jsonrpc": "2.0", "id": req_id}

        try:
            if method == "initialize":
                response["result"] = await handle_initialize(params)
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response["result"] = await handle_tools_list(params)
            elif method == "tools/call":
                response["result"] = await handle_tools_call(params)
            elif method == "ping":
                response["result"] = {}
            else:
                response["error"] = {"code": -32601, "message": f"Method '{method}' not found"}
        except Exception as ex:
            response["error"] = {"code": -32603, "message": str(ex)}

        out_line = json.dumps(response, ensure_ascii=False) + "\n"
        sys.stdout.write(out_line)
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        asyncio.run(run_mcp_server())
    except (KeyboardInterrupt, SystemExit):
        pass
