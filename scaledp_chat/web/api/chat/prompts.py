from langchain_core.prompts import ChatPromptTemplate

rag_prompt = ChatPromptTemplate.from_template(
    "You are an assistant for "
    "question-answering tasks. Use the "
    "following pieces of retrieved context to "
    "answer the question. If you don't know the answer, just say that you don't know. "
    "Please add to the output python code snippets if need and for create spark "
    "session please use ScaleDPSession and read files using "
    "`spark.read.format('binaryFile')` and show_image, show_text, show_ner, "
    "show_json methods of the DataFrame. Be "
    "concise.\nQuestion: {"
    "question} \nContext: {context} \nAnswer:",
)

defenition_prompt = ChatPromptTemplate.from_template(
    "From the question extract python function and class names as CSV."
    "If question does'nt contain any function or class names return empty string."
    "\nQuestion: {"
    "question} \nAnswer:",
)
