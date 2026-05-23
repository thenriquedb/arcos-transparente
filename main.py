from langchain.agents import create_agent
from dotenv import load_dotenv
from pprint import pprint
from agents.tools.registry import get_all_tools

load_dotenv()


def criar_agente():
    tools = get_all_tools()

    system_prompt = (
        "Você é um assistente que ajuda a buscar informações sobre servidores "
        "públicos. Sempre que a pergunta depender de dados do sistema, use as "
        "tools disponíveis antes de responder. Para consultas por nome, "
        "secretaria, cargo ou mês de referência, prefira as tools de servidores "
        "em vez de responder de memória."
    )

    return create_agent(
        tools=tools,
        model="gpt-4o-mini",
        system_prompt=system_prompt,
    )


if __name__ == "__main__":
    agente = criar_agente()
    resultado = agente.invoke({"messages": ["Quais os 10 maiores salários da prefeitura?"]})

    # pprint(resultado)
    print(resultado["messages"][-1].content)
