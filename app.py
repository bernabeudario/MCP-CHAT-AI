from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from typing import List
import asyncio
import nest_asyncio
import os
import json

nest_asyncio.apply()

load_dotenv()

class MCP_CHAT_AI:

    def __init__(self, config_file: str = "server_config.json"):
        self.config_file: str = config_file
        self.client: OpenAI = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.available_tools: List[dict] = []
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self.sessions: dict = {}
        self.chat_history = []
        
    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """
        Conecta a un servidor MCP específico
        
        Args:
            server_name: Nombre del servidor
            server_config: Configuración del servidor
        """
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            try:
                # Tools disponibles
                response = await session.list_tools()
                print(f"🔧 Tools disponibles para '{server_name}':", [tool.name for tool in response.tools])
                for tool in response.tools:
                    self.sessions[tool.name] = session
                    self.available_tools.append({
                        'type': 'function',
                        'function': {
                            'name': tool.name,
                            'description': tool.description,
                            'parameters': tool.inputSchema
                        }
                    })
            
            except Exception as e:
                print(f"❌ Error al listar tools en '{server_name}': {e}")
                
        except Exception as e:
            print(f"❌ Error al conectar con '{server_name}': {e}")

    async def connect_to_servers(self) -> None:
        """Conecta a todos los servidores MCP configurados"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})

            if not servers:
                print("⚠️ No se encontraron servidores en la configuración.")
                return

            for name, config in servers.items():
                await self.connect_to_server(name, config)

        except Exception as e:
            print(f"❌ Error al cargar la configuración del servidor: {e}")
            raise

    async def process_query(self, query: str) -> None:
        """Procesa una consulta del usuario y gestiona el ciclo de herramientas si es necesario."""

        self.chat_history.append({'role': 'user', 'content': query})
        while True:
            try:
                response = self.client.chat.completions.create(
                    max_tokens=2024,
                    model='gemini-2.0-flash',
                    tools=self.available_tools,
                    messages=self.chat_history
                )
                        
                if response.choices[0].finish_reason == 'stop':
                    self.chat_history.append({'role': 'assistant', 'content': response.choices[0].message.content})
                    print(f"🤖 Bot: {response.choices[0].message.content}")
                    break
                elif response.choices[0].finish_reason == 'tool_calls':
                    tool_call = response.choices[0].message.tool_calls[0]
                    tool_id = tool_call.id
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    session = self.sessions.get(tool_name)
                    print(f"---->🔧 Utilizando tool '{tool_name}': {tool_args}")
                    self.chat_history.append({
                        'role': 'assistant',
                        'tool_calls': [
                            {
                                'id': tool_id,
                                'function': {
                                    'name': tool_name,
                                    'arguments': f'{tool_args}'
                                }
                            }
                        ]
                    })
                    tool_result = await session.call_tool(tool_name, arguments=tool_args)
                    self.chat_history.append({
                        'role': 'tool',
                        'tool_call_id': tool_id,
                        'content': tool_result.content[0].text
                    })
                else:
                    #print(f"⚠️ Finish_reason inesperado: {response.choices[0].finish_reason}")
                    print(f"⚠️ Reintentando...")
                    #break
            except Exception as e:
                import traceback
                print(f"❌ Error en la comunicación con el modelo: {e}")
                traceback.print_exc()
                break

    async def chat_loop(self) -> None:
        """Bucle principal del chat"""
        print("\n🤖 Bienvenido al Chat AI con Tools MCP!")
        print("📝 Escribe tu consulta ('salir' para cerrar)")
        
        while True:
            try:
                query = input("\n👤 Usuario: ").strip()
                print() 
                
                if query.lower() in ['salir', 'exit', 'quit']:
                    print("👋 Chau")
                    break
                
                if not query:
                    continue
                
                await self.process_query(query)
                
            except KeyboardInterrupt:
                print("\n👋 Chau")
                break
            except Exception as e:
                print(f"❌ Error en el bucle del chat: {e}")

    async def cleanup(self) -> None:
        """Limpia los recursos utilizados"""
        await self.exit_stack.aclose()

async def main() -> None:
    """Función principal"""
    chatbot = MCP_CHAT_AI()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
