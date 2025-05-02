from langchain_core.prompts import ChatPromptTemplate

rag_prompt = ChatPromptTemplate.from_template(
    "You are an assistant for "
    "question-answering tasks. Use the "
    "following pieces of retrieved context to "
    "answer the question. If you don't know the answer, just say that you don't know. "
    "Please add to the output python code snippets if need and for create spark "
    "session please use ScaleDPSession and read files using "
    "`spark.read.format('binaryFile')`. Be concise.\nQuestion: {"
    "question} \nContext: {context} \nAnswer:",
)
