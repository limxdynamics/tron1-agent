from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain_core.prompts import PromptTemplate

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
#from langchain_openai import ChatOpenAI
import logging
logger = logging.getLogger(__name__)
prompt_template = """请根据以下上下文回答最后的问题。如果上下文没有该答案，则不需要参考上下文直接响应，而且回复中可以增加‘我还在学习’的字眼，不要有‘上下文未涉及‘的字眼。回答应简洁明了，最多使用三句话，确保直接针对问题。

{context}

问题：{question}"""
class _LLM:
    def __init__(self,llm_model):
        self.llm=llm_model

    def invoke(self, query):
        try:
            
            dialogue = [{"role": "user", "content": str(query).replace('text=',"")}]
            # 调用 LLM 的 response 方法
            responses = self.llm.response(dialogue)
            
            # 将生成的响应拼接成完整文本
            full_response = ''.join(responses)
            return full_response
        except Exception as e:
            logger.error(f"Error in LLM response generation: {e}")
            return "An error occurred while generating the response."
    def __call__(self, inputs):
        """
        使 _LLM 实例可调用，兼容 LangChain 的链式调用。
        :param inputs: 输入的查询
        :return: LLM 的响应
        """
        return self.invoke(inputs)
    
class Rag:
    _instance = None

    def __new__(cls, llm,config: dict=None):
        if cls._instance is None:
            cls._instance = super(Rag, cls).__new__(cls)
            cls._instance.init(llm, config or {})  # 初始化实例属性
        return cls._instance

    def init(self, llm,config: dict):
        self.doc_path = config.get("doc_path")
        self.emb_model = config.get("emb_model")
        self.template = prompt_template
        self.custom_rag_prompt = PromptTemplate.from_template(self.template)
        self.llm = _LLM(llm)
        # 定义加载器，支持不同文档类型
        loader = DirectoryLoader(
            self.doc_path,
            glob="**/*.txt",
            loader_cls= TextLoader
        )
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True}
        embedding_model = HuggingFaceBgeEmbeddings(model_name=self.emb_model
                                                   , model_kwargs=model_kwargs
                                                   , encode_kwargs=encode_kwargs)

        #embeddings = embedding_model.embed_documents([doc.content for doc in documents])
        #vector_store = FAISS.from_embeddings(documents=splits, embedding=embeddings)
        vector_store = Chroma.from_documents(documents=splits, embedding=embedding_model)
        self.retriever = vector_store.as_retriever()

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        self.rag_chain = (
                {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
                | self.custom_rag_prompt
                | self.llm
                | StrOutputParser()
        )

    def query(self, query):
        result = self.rag_chain.invoke(query)
        return f"Help you find the information related to {query}," + str(result)
    def classify_query(self, query: str) -> bool:
        """
        判断 query 是否可能在本地知识库中找到答案。
        :param query: 用户问题
        :return: 如果可能在知识库中找到答案，返回 True；否则返回 False。
        """
        docs = self.retriever.get_relevant_documents(query)
        return len(docs) > 0

if __name__ == "__main__":
    from llm import OpenAILLM
    # 配置
    config = {
        "doc_path": "documents",  # 本地知识库路径
        "emb_model": "models/bge-small-zh",  # 嵌入模型
        "model_name": "qwen3:1.7b",  # LLM 模型
        "base_url": "http://127.0.0.1:11434/v1",  # OpenAI API 基础 URL
        "api_key": "ollama",  # OpenAI API 密钥
    }

    model_name = config.get("model_name")
    api_key = config.get("api_key")
    base_url = config.get("base_url")
    client = OpenAILLM({"model_name":model_name, "api_key":api_key, "url":base_url})

    # 初始化 RAG 系统
    rag = Rag(client, config)

    # 示例查询
    queries = [
        "LimX Dynamics是一家怎样的公司",
        "今天的天气怎么样？",
        "什么是LangChain？",
    ]

    for query in queries:
        print(f"Query: {query}")
        print("Answer from RAG:")
        print(rag.query(query))