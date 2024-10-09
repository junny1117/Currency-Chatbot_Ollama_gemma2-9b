import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.chat_models import ChatOllama
from langchain.chains import RetrievalQA
from langchain.schema.runnable import RunnableMap
from langchain.prompts import ChatPromptTemplate

def currency_info(search):
    url = f'https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=환율{search}'
    
    options = webdriver.EdgeOptions()
    options.add_argument("--headless")
    driver = webdriver.Edge(options=options)
    
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//a[@class="f_etit"]'))
    )


    country = driver.find_element(By.XPATH, '//a[@class="f_etit"]').text.strip()
    rate = driver.find_element(By.XPATH, '//em[@class="txt_num"]').text.strip()
    time_info = driver.find_element(By.XPATH, '//*[@id="exchangeColl"]/div[3]/div/div[3]/div[2]/div[2]/span[1]').text.strip()
    gap_element = driver.find_element(By.XPATH, '//dl[@class="dl_comm"]/dd[1]').text.strip()
    gap = gap_element.split()[-1]  
    gap_percent = driver.find_element(By.XPATH, '//dl[@class="dl_comm"]/dd[2]').text.strip()
    
    buy = driver.find_element(By.XPATH, '//td[text()="살 때"]/following-sibling::td').text.strip()
    sell = driver.find_element(By.XPATH, '//td[text()="팔 때"]/following-sibling::td').text.strip()
    send = driver.find_element(By.XPATH, '//td[text()="보낼 때"]/following-sibling::td').text.strip()
    receive = driver.find_element(By.XPATH, '//td[text()="받을 때"]/following-sibling::td').text.strip()

    app_data = {
            "기준시각": time_info,
            "국가명": country,
            "환율": rate,
            "어제대비": gap,
            "어제대비(%)": gap_percent,
            "현찰 살때": buy,
            "현찰 팔때": sell,
            "송금 보낼때": send,
            "송금 받을때": receive
        }

    driver.quit()
    return app_data

def main():
    st.title("환율 정보 제공 챗봇")
    search = st.text_input("국가 이름을 입력하세요:(예: 미국)", "")
    query = st.text_input("궁금한 것을 입력하세요:(예: 환율, 송금 보낼때, 현찰 살때)", "")
    
    if st.button("제출"):
        data = currency_info(search)

        document = Document(page_content="\n".join([f"{key}: {str(data[key])}" for key in ['기준시각', '국가명', '환율', '어제대비', 
                                                                                            '어제대비(%)', '현찰 살때', '현찰 팔때',
                                                                                            '송금 보낼때', '송금 받을때']]))

        text_splitter = RecursiveCharacterTextSplitter(separators=",")
        docs = text_splitter.split_documents([document])

        embedding_function = SentenceTransformerEmbeddings(model_name="jhgan/ko-sroberta-multitask")

        db = FAISS.from_documents(docs, embedding_function)
        retriever = db.as_retriever(search_type="similarity", search_kwargs={'k':10, 'fetch_k': 100})
        
        if query:
            query_result = db.similarity_search(query)

            llm = ChatOllama(model="gemma2:9b", temperature=0.3)

            template = """
            당신은 환율정보를 알려주는 챗봇입니다. 사용자에게 가능한 많은 정보를 제공하세요.
            반드시 환율 관련 질문에만 답변하세요.
            Answer the question based only on the following context:
            {context}

            Question: {question}
            """
            prompt = ChatPromptTemplate.from_template(template)

            chain = RunnableMap({
                "context": lambda x: retriever.get_relevant_documents(x['question']),
                "question": lambda x: x['question']
            }) | prompt | llm

            question = query
            if question:
                response = chain.invoke({'question': question})
                st.markdown(response.content)

if __name__ == "__main__":
    main()
