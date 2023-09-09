from dash import Input, Output
from functions import *
from layout import *
import io

@app.callback(
    [Output('greeting', 'children'), 
     Output('download', 'data'), 
     Output('success-msg', 'style'),
     Output('upload-data', 'contents')],
    [Input('upload-data', 'contents')]
)
def update_output(contents):
    if contents is None:
        return "Upload .xlsx file to Begin", None, {'display':'none'}, None

    content_type, content_string = contents.split(',')
    decoded_content = base64.b64decode(content_string)
    
    ads, mods = clean_ads_data(io.BytesIO(decoded_content))
    ads_df = norm_ads(ads)
    mods_df = norm_mods(mods)
    
    download_data = optimise(ads_df, mods_df)
    
    return "File processed successfully!", download_data, {'display':'inline-block'}, None