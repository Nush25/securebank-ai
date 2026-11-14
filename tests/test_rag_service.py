
from backend.app.services.rag_service import ask_banking_assistant


questions = [
    "What is UPI and how does it work?",
    "What is the difference between NEFT and RTGS?",
    "How can I apply for a personal loan?",
    "What is a credit card?",
    "what happen if i share my otp with someone?",
    "How much maximum personal loan bank gives?"
]


if __name__ == "__main__":

    for question in questions:

        print("\n" + "=" * 60)
        print("QUESTION:", question)
        print("=" * 60)

        result = ask_banking_assistant(question)

        print("\nANSWER:")
        print(result["answer"])

        print("\nSOURCES:")

        for source in result["sources"]:
            print(
                f"- {source['filename']} "
                f"(similarity: {source['similarity']:.3f})"
            )
