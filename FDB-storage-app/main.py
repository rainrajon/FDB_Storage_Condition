
import os
import requests
import json
import openai
# from langchain.llms import AzureOpenAI
import openai
import time
from extract import *
from datetime import datetime
now = datetime.now()
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
from utilities import *
from configs import *
import uuid
from logger import *
import logging
load_dotenv()

# initializing application variables
openai.api_key = os.environ.get("AZURE_OPENAI_KEY")
openai.api_base = os.environ.get("AZURE_OPENAI_ENDPOINT") 
openai.api_type = 'azure'
openai.api_version = '2023-05-15' # this may change in the future
deployment_name=os.environ.get('DEPLOYMENT_NAME')

#read from prompt json file in blob

# prompt=read_from_blob(prompt_json_folder,prompt_json_filename)
# prompt = json.loads(prompt.decode('utf-8'))
# prompt_ocr=prompt['prompt 1']['prompt']

# prompt_xml=prompt['prompt 2']['prompt']

prompt = json.load(open('prompt_json.json','r'))
prompt_ocr=prompt['prompt 1']['prompt']

#read spl key from blob
# spl_key=read_from_blob(spl_key_folder,spl_key)
# spl_key_df=pd.read_csv(BytesIO(spl_key))
spl_key_df=pd.read_csv('SPL_Key.csv')
ndc_list=list(spl_key_df['Converted_NDC'].value_counts().index)
batch_id=now.strftime("%m%d%Y")
def batch_predict():
    #read blob images from batch folder
    blob_list=read_blob_batch(batch_id)

    response={'NDC':'','Storage_Condition':'','Reason':'','Status':'','created_date':'','GUID':'','execution_time':'','prompt_id':'','error_msg':'','response_status_code':'','batch_id':'','img_loc':''}
    results=pd.DataFrame(columns=response.keys())
    count=0

    for blob in blob_list:
        print(blob.name)
        # if '2023' in blob.name:
        #     break
        count+=1
        if count==10:
            break
   
        set_id=blob.name.split('/')[-2]
        
        response={'NDC':'','Storage_Condition':'','Reason':'','Status':'','created_date':'','GUID':'','execution_time':'','prompt_id':'','error_msg':'','response_status_code':'','batch_id':'','img_loc':''}
        
        if ".jpg" in blob.name or ".png" in blob.name:
            # print(blob.name)
            t1=time.time()
            GUID=str(uuid.uuid4())
            img_bytes=read_from_blob('',blob.name)
            ocr_text=ocr(img_bytes)
            ocr_text=extract_text(ocr_text[0])
            # print(ocr_text)
            if ocr_text==None:
                #logging
                logging.warning("{0}:{1}:{2}:{3}".format(GUID,blob.name,'','OCR Text not found'))
                continue
            response['GUID']=GUID
            response['img_loc']=str(blob.name)
            response['batch_id']=batch_id
            #upload ocr to blob
            # upload_json_to_blob(ocr_folder,GUID,ocr_text)
            ndc1=ndc_regex(ocr_text)
            ndc=ndc_conversion(ndc1)
            print('converted ndc after ocr',ndc)
            if ndc==None:
                #logging 'NDC validation failed'
                logging.warning("{0}:{1}:{2}:{3}".format(GUID,blob.name,ndc1,'OCR NDC validation failed'))
                continue
            
            elif ndc !=None and ndc in ndc_list:
                #response from openai
                gpt_response=llm_response(ocr_text,prompt_ocr,ndc)
                # print(gpt_response)
                response['Storage_Condition']=gpt_response['Storage_Condition']
                # llm_ndc=ndc_conversion(gpt_response['NDC'])
                print('Final ndc',gpt_response['NDC'])
                # if llm_ndc==None:
                #     #logging
                #     logging.warning("{0}:{1}:{2}:{3}".format(GUID,blob.name,gpt_response['NDC'],'LLM NDC validation failed'))
                #     # response['Storage_Condition']=gpt_response['Storage_Condition']
                #     continue
                # else:
                response['NDC']=gpt_response['NDC']
                response['Reason']=gpt_response['Reason']
                response['created_date']=now.strftime("%m/%d/%Y %H:%M:%S")
                response['prompt_id']='prompt 1'               
                if response_validation(response):
                    response['Status']='success'
                else:
                    response['Status']='failure'
                    response['error_msg']='Response Validation failed'
                    logging.warning("{0}:{1}:{2}:{3}".format(GUID,blob.name,response['NDC'],'Response Validation failed'))
            elif ndc !=None and ndc not in ndc_list:
                response['Status']='failure'
                # response['Reason']= 'NDC not in spl key'
                response['NDC']=ndc
                response['created_date']=now.strftime("%m/%d/%Y %H:%M:%S")
                #logging
                logging.warning("{0}:{1}:{2}:{3}".format(GUID,blob.name,response['NDC'],'NDC not found in SPL key'))
                response['error_msg']='NDC not found in SPL key'
            
            t2 = time.time()
            execution_time=t2-t1
            response['execution_time']=execution_time
            logging.info("{0}: Response body: {1}".format(GUID,response))
            for i in response.keys():
                response[i]=[response[i]]
                
            results=pd.concat([results,pd.DataFrame(response)],axis=0)
            
        else:
            continue
        
              
    spl_key_df.rename(columns = {"Converted_NDC": "NDC","NDC":"NDC10"},inplace = True)
    results=results.merge(spl_key_df[['ProprietaryName','DocID','SetID','NDC','S3Key','NDC11']],on='NDC',how='left')
    
    #fetching unique ndcs
    plan_a=unique_ndc(results)
    print('plan A df',plan_a)

    dff=plan_a[plan_a['Storage_Condition']=='Undetermined']

    plan_a.to_csv('Output/output.csv')

    #implement plan b which will fetch responses for dff and then update in plan a and create a final_df


    # upload_to_table(response,final_df)
    
    return {"message":'success'}
