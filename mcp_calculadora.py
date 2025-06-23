from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("calculadora")

@mcp.tool()
def multiplicar(numero_01: float, numero_02: float) -> str:
    """
    Multiplicar dos números
    
    Args:
        numero_01: Primer número a multiplicar
        numero_02: Segundo número a multiplicar
        
    Returns:
        El resultado de la multiplicación
    """
    try:
        return str(numero_01 * numero_02)
    except Exception as e:
        return f"Error al multiplicar: {str(e)}"

@mcp.tool()
def dividir(numero_01: float, numero_02: float) -> str:
    """
    Dividir dos números
    
    Args:
        numero_01: Primer número a dividir
        numero_02: Segundo número a dividir
        
    Returns:
        El resultado de la división
    """
    try:
        return str(numero_01 / numero_02)
    except Exception as e:
        return f"Error al dividir: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')