from main import criar_agente, config

agente = criar_agente()

print("=== Chat de Teste de Memória ===")
print("Digite 'sair' para encerrar\n")

while True:
    pergunta = input("Você: ").strip()

    if not pergunta:
        continue

    if pergunta.lower() == "sair":
        print("Encerrando chat.")
        break

    try:
        resultado = agente.invoke({"messages": [pergunta]}, config=config)
        resposta = resultado["messages"][-1].content
        print(f"\nAgente: {resposta}\n")
    except ValueError as e:
        print(f"\n[Guardrail] {e}\n")
    except Exception as e:
        print(f"\n[Erro] {e}\n")
