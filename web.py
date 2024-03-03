from concurrent.futures import ThreadPoolExecutor
from scipy.spatial.distance import cosine
from transformers import AutoTokenizer
from urllib.parse import quote
from openai import AzureOpenAI
from bs4 import BeautifulSoup
from fastapi import FastAPI
import markdownify
import unicodedata
import requests
import time
import re

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mixtral-8x7b-instruct-v0.1")

app = FastAPI()

client = AzureOpenAI(
    api_key="6b8028d8573f4bc1aa63e5f28801d3c0",
    azure_endpoint="https://deepnight-ai.openai.azure.com/",
    api_version="2024-02-15-preview",
)

start_time = None

def calculate_similarity(embedding1, embedding2):
    # Calculate the cosine similarity which is 1 - cosine distance
    similarity = 1 - cosine(embedding1, embedding2)
    return similarity


def similarity_search(query, contents):
    # Generate an embedding for the query
    query_embedding = gen_embedding(query)

    # List to hold all chunks with their similarity score
    all_chunks_with_similarity = []

    # Iterate over all contents
    for content in contents:
        chunks_with_embeddings = content["chunks_with_embeddings"]

        # Iterate over all chunks in the content
        for chunk in chunks_with_embeddings:
            chunk_text = chunk["text"]
            chunk_embedding = chunk["vectors"]

            # Calculate similarity score
            similarity_score = calculate_similarity(query_embedding, chunk_embedding)

            # Append the chunk text and similarity score to the list
            all_chunks_with_similarity.append((chunk_text, similarity_score))

    # Sort the list based on similarity score in descending order
    all_chunks_with_similarity.sort(key=lambda x: x[1], reverse=True)

    # Return the top-3 results
    top_3_results = all_chunks_with_similarity[:5]

    return top_3_results


def extract_info(elm):
    temp = {}
    temp["title"] = elm.find(class_="BNeawe vvjwJb AP7Wnd").text
    link = elm.find("a").get("href")
    temp["link"] = link.split("/url?q=")[1].split("&sa")[0]
    desc = elm.find(class_="BNeawe s3v9rd AP7Wnd").text
    temp["description"] = desc
    return temp


def get_organic_search_results(result):
    try:
        temp = {}
        temp["title"] = unicodedata.normalize(
            "NFKD",
            result.find(attrs={"data-snf": "x5WNvb"})
            .find(attrs={"jsname": "UWckNb"})
            .find("h3", class_="LC20lb MBeuO DKV0Md")
            .text,
        )
        temp["link"] = unicodedata.normalize(
            "NFKD",
            result.find(attrs={"data-snf": "x5WNvb"})
            .find(attrs={"jsname": "UWckNb"})
            .get("href"),
        )
        temp["description"] = unicodedata.normalize(
            "NFKD", result.find(attrs={"data-snf": "nke7rc"}).find("span").text
        )
        return temp
    except:
        return None


def get_google_search_results(query):
    global start_time
    start_time = time.time()
    query = quote(query)
    page = requests.get(
        f"https://www.google.com/search?q={query}",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Content-Type": "text/html; charset=UTF-8",
        },
    )
    if page.status_code == 200:
        page = page.text
        # with open("google_search_page.html", "w", encoding="utf-8") as f:
        #     f.write(page)
    else:
        return False

    soup = BeautifulSoup(page, "html.parser")
    # scrapping the elements...
    # 1. find result-stats from element with id="result-stats"
    result_stats = soup.find(id="result-stats").text  # type->str
    search_box = soup.find(id="search")  # type->element
    search_focus = search_box.find(class_="dURPMd")  # type->element
    answerbox = search_focus.find(class_="ULSxyf")  # type->element
    answerbox_result = {}
    # Let's go for time...
    if answerbox:
        if answerbox.find(class_="vk_gy vk_sh card-section sL6Rbf"):
            main_element_for_answerbox = answerbox.find(
                class_="vk_gy vk_sh card-section sL6Rbf"
            )  # type->element
            answerbox_heading = unicodedata.normalize(
                "NFKD",
                main_element_for_answerbox.find(
                    class_="gsrt vk_bk FzvWSb YwPhnf", attrs={"role": "heading"}
                ).text,
            )  # type->str
            answerbox_additional_context = main_element_for_answerbox.find_all(
                class_="vk_gy vk_sh"
            )
            answerbox_additional_context = [
                x.text for x in answerbox_additional_context
            ]
            answerbox_additional_context = " ".join(answerbox_additional_context)
            answerbox_result["type"] = "time"
            answerbox_result["time"] = answerbox_heading
            answerbox_result["date"] = unicodedata.normalize(
                "NFKD", answerbox_additional_context
            )
        elif answerbox.find("h2", class_="bNg8Rb OhScic zsYMMe BBwThe"):
            # let's see if it is the weather....
            weather_box = (
                True
                if "Weather"
                in answerbox.find("h2", class_="bNg8Rb OhScic zsYMMe BBwThe").text
                else False
            )
            if weather_box:
                weather_box = answerbox.find("div", class_="nawv0d", id="wob_wc")
                weather_info_box = weather_box.find("div", class_="UQt4rd")
                weather_info = {
                    "type": "weather",
                    "condition": {
                        "text": weather_info_box.find("img", class_="wob_tci").get(
                            "alt"
                        ),
                        "image": "https:"
                        + weather_info_box.find("img", class_="wob_tci").get("src"),
                    },
                    "temperature": [
                        {
                            "unit": unicodedata.normalize(
                                "NFKD",
                                weather_info_box.find(
                                    attrs={
                                        "jscontroller": "e0Sh5",
                                        "jsaction": "rcuQ6b:npT2md",
                                    },
                                    class_="vk_bk wob-unit",
                                )
                                .find_all("a", class_="wob_t")[0]
                                .find("span")
                                .text,
                            ),
                            "value": unicodedata.normalize(
                                "NFKD",
                                weather_info_box.find(
                                    "div", class_="vk_bk TylWce SGNhVe"
                                )
                                .find_all("span", class_="wob_t")[0]
                                .text,
                            ),
                        },
                        {
                            "unit": unicodedata.normalize(
                                "NFKD",
                                weather_info_box.find(
                                    attrs={
                                        "jscontroller": "e0Sh5",
                                        "jsaction": "rcuQ6b:npT2md",
                                    },
                                    class_="vk_bk wob-unit",
                                )
                                .find_all("a", class_="wob_t")[1]
                                .find("span")
                                .text,
                            ),
                            "value": unicodedata.normalize(
                                "NFKD",
                                weather_info_box.find(
                                    "div", class_="vk_bk TylWce SGNhVe"
                                )
                                .find_all("span", class_="wob_t")[1]
                                .text,
                            ),
                        },
                    ],
                    "additional": [
                        x.text
                        for x in weather_info_box.find("div", class_="wtsRwe").find_all(
                            "div"
                        )
                    ],
                    "forecast": [
                        {
                            "day": unicodedata.normalize(
                                "NFKD", x.find(class_="Z1VzSb").text
                            ),
                            "condition": x.find(class_="DxhUm")
                            .find("g-img")
                            .find("img")
                            .get("alt"),
                            "temperature": {
                                "highest": [
                                    {
                                        "unit": unicodedata.normalize(
                                            "NFKD",
                                            weather_info_box.find(
                                                attrs={
                                                    "jscontroller": "e0Sh5",
                                                    "jsaction": "rcuQ6b:npT2md",
                                                },
                                                class_="vk_bk wob-unit",
                                            )
                                            .find_all("a", class_="wob_t")[0]
                                            .find("span")
                                            .text,
                                        ),
                                        "value": unicodedata.normalize(
                                            "NFKD",
                                            x.find(class_="wNE31c")
                                            .find(class_="gNCp2e")
                                            .find_all("span", class_="wob_t")[0]
                                            .text,
                                        ),
                                    },
                                    {
                                        "unit": unicodedata.normalize(
                                            "NFKD",
                                            weather_info_box.find(
                                                attrs={
                                                    "jscontroller": "e0Sh5",
                                                    "jsaction": "rcuQ6b:npT2md",
                                                },
                                                class_="vk_bk wob-unit",
                                            )
                                            .find_all("a", class_="wob_t")[1]
                                            .find("span")
                                            .text,
                                        ),
                                        "value": unicodedata.normalize(
                                            "NFKD",
                                            x.find(class_="wNE31c")
                                            .find(class_="gNCp2e")
                                            .find_all("span", class_="wob_t")[1]
                                            .text,
                                        ),
                                    },
                                ],
                                "lowest": [
                                    {
                                        "unit": unicodedata.normalize(
                                            "NFKD",
                                            weather_info_box.find(
                                                attrs={
                                                    "jscontroller": "e0Sh5",
                                                    "jsaction": "rcuQ6b:npT2md",
                                                },
                                                class_="vk_bk wob-unit",
                                            )
                                            .find_all("a", class_="wob_t")[0]
                                            .find("span")
                                            .text,
                                        ),
                                        "value": unicodedata.normalize(
                                            "NFKD",
                                            x.find(class_="wNE31c")
                                            .find(class_="QrNVmd ZXCv8e")
                                            .find_all("span", class_="wob_t")[0]
                                            .text,
                                        ),
                                    },
                                    {
                                        "unit": unicodedata.normalize(
                                            "NFKD",
                                            weather_info_box.find(
                                                attrs={
                                                    "jscontroller": "e0Sh5",
                                                    "jsaction": "rcuQ6b:npT2md",
                                                },
                                                class_="vk_bk wob-unit",
                                            )
                                            .find_all("a", class_="wob_t")[1]
                                            .find("span")
                                            .text,
                                        ),
                                        "value": unicodedata.normalize(
                                            "NFKD",
                                            x.find(class_="wNE31c")
                                            .find(class_="QrNVmd ZXCv8e")
                                            .find_all("span", class_="wob_t")[1]
                                            .text,
                                        ),
                                    },
                                ],
                            },
                        }
                        for x in weather_box.find(class_="R3Y3ec rr3bxd")
                        .find(class_="wob_dfc", id="wob_dp")
                        .find_all(class_="wob_df")
                    ],
                }

                answerbox_result = weather_info
        elif answerbox.find("h2", class_="bNg8Rb OhScic zsYMMe BBwThe"):
            if (
                "Calculator"
                in answerbox.find("h2", class_="bNg8Rb OhScic zsYMMe BBwThe").text
            ):
                calculator = answerbox.find("div", class_="card-section")
                display_field = (
                    calculator.find("div", class_="BRpYC")
                    .find(attrs={"jsname": "a1lrmb"}, class_="TIGsTb")
                    .find(attrs={"jsname": "DjP6yd"}, class_="fB3vD")
                )
                answerbox_result = {
                    "type": "calculator",
                    "answer": unicodedata.normalize(
                        "NFKD",
                        display_field.find(class_="qv3Wpe").text.rstrip().lstrip(),
                    ),
                }
        else:
            if answerbox.find("div", class_="fKw1wf osrp-blk"):
                if (
                    "Stock"
                    in answerbox.find("div", class_="fKw1wf osrp-blk")
                    .find(attrs={"jscontroller": "ij8bP"})
                    .find(class_="gT9M5c")
                    .find(class_="kLt6Mb q8U8x")
                    .text
                ):
                    main_unit = (
                        answerbox.find("div", class_="fKw1wf osrp-blk")
                        .find(attrs={"jscontroller": "ij8bP"})
                        .find(attrs={"jscontroller": "uc1Yvc"})
                        .find(class_="aviV4d")
                    )
                    dx__ = {}
                    dx__["type"] = ("stocks",)
                    dx__["company_name"] = main_unit.find(class_="aMEhee PZPZlf").text
                    current_point_box = main_unit.find(class_="wGt0Bc")
                    dx__["stock_value"] = (
                        current_point_box.find(class_="IsqQVc NprOob wT3VGc")
                        .text.lstrip()
                        .rstrip()
                    )
                    dx__["currency"] = (
                        current_point_box.find(class_="knFDje").text.lstrip().rstrip()
                    )
                    dx__["change"] = (
                        current_point_box.find(class_="WlRRw IsqQVc fw-price-up")
                        .find(attrs={"jsname": "qRSVye"})
                        .text.lstrip()
                        .rstrip()
                    )
                    dx__["change_percent"] = (
                        current_point_box.find(class_="jBBUv")
                        .find(attrs={"jsname": "rfaVEf"})
                        .text.lstrip()
                        .rstrip()
                        .split("(")[1]
                        .split(")")[0]
                    )
                    dx__["status"] = {
                        "live": unicodedata.normalize(
                            "NFKD",
                            current_point_box.find(
                                class_="TgMHGc", attrs={"jscontroller": "MnCoi"}
                            ).text,
                        ),
                        "hours": unicodedata.normalize(
                            "NFKD",
                            current_point_box.find(
                                class_="qFiidc", attrs={"jscontroller": "MIgmof"}
                            ).text,
                        ),
                    }

                    answerbox_result = dx__

            else:
                answerbox_result = {"type": "unknown"}

    # Now let's get the organic search results:
    organic_search_results = []
    with ThreadPoolExecutor() as executor:
        results = executor.map(
            get_organic_search_results,
            search_focus.find_all(class_="g Ww4FFb vt6azd tF2Cxc asEBEc"),
        )
        for result in results:
            if result != None:
                organic_search_results.append(result)

    # SEARCH_RESULTS.insert_one(
    #     {
    #         "dt": str(datetime.datetime.now()),
    #         "time_taken": str(time.time() - start_time),
    #         "answerbox": answerbox_result,
    #         "organic_search_results": organic_search_results,
    #     }
    # )

    return {
        "answerbox": answerbox_result,
        "organic_search_results": organic_search_results,
    }


def gen_embedding(text):
    embedding = client.embeddings.create(input=text, model="embeddings")
    return embedding.data[0].embedding


def gen_desc_embeddings(results):
    organic_search_results = results.get("organic_search_results", [])

    # Define a function that takes a single search result and generates its embedding
    def generate_and_save_embedding(result):
        description = result.get("description", "")
        embedding = gen_embedding(description)
        result["embedding"] = embedding
        # Assuming there's a mechanism to save the result, e.g., to a database
        # Here we just return the result with the embedding
        return result

    # Use ThreadPoolExecutor to run generate_and_save_embedding function in parallel for all search results
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(generate_and_save_embedding, result)
            for result in organic_search_results
        ]
        completed_results = [future.result() for future in futures]

    return completed_results


def gen_embedding(text):
    embedding = client.embeddings.create(input=text, model="embeddings")
    return embedding.data[0].embedding


def split_into_chunks(content):
    chunk_size = 500
    encoded = tokenizer.encode(content)
    chunks = []
    for i in range(0, len(encoded), chunk_size):
        chunk_encoded = encoded[i : i + chunk_size]
        chunk = tokenizer.decode(chunk_encoded)
        chunks.append(chunk)
    return chunks


# def navigate_and_extract(driver, url):
#     driver.get(url)
#     page_content = driver.page_source
#     soup = BeautifulSoup(page_content, 'html.parser')
#     for tag in soup(['style', 'head', 'form', 'button', 'script', 'link', 'video', 'audio', 'center', 'input', 'textarea']):
#         tag.extract()
#     markdown_content = markdownify.markdownify(str(soup))
#     markdown_content = markdown_content.replace("\n\n", "")

#     content = ""
#     for line in markdown_content.splitlines():
#         if not re.match(r'^\s*$', line):  # This will be True if the line is not empty and not just blank spaces
#             content += line


#     chunks = split_into_chunks(content)
#     return {
#         "content": content,
#         "chunks": chunks
#     }


def navigate_and_extract(driver, url):
    driver.get(url)
    page_content = driver.page_source
    soup = BeautifulSoup(page_content, "html.parser")
    for tag in soup(
        [
            "style",
            "head",
            "form",
            "button",
            "script",
            "link",
            "video",
            "audio",
            "center",
            "input",
            "textarea",
        ]
    ):
        tag.extract()
    markdown_content = markdownify.markdownify(str(soup))
    markdown_content = markdown_content.replace("\n\n", "")

    content = ""
    for line in markdown_content.splitlines():
        if not re.match(
            r"^\s*$", line
        ):  # This will be True if the line is not empty and not just blank spaces
            content += line

    chunks = split_into_chunks(content)

    # Generate embeddings for each chunk in parallel
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(gen_embedding, chunk) for chunk in chunks]
        embeddings = [future.result() for future in futures]

    # Combine chunks with their embeddings
    results = [
        {"text": chunk, "vectors": embedding}
        for chunk, embedding in zip(chunks, embeddings)
    ]

    return {"content": content, "chunks_with_embeddings": results}
