import base64
from datetime import timedelta

import cufflinks as cf
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib import pyplot as plt
from IPython.display import display

# Web App Title

# Config app
cf.set_config_file(sharing='public', theme='ggplot', offline='True')
st.set_page_config(page_title='Reporte Sharp', page_icon=':bar_chart:')
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden; }
    footer {visibility: hidden;}
    </style>
"""

st.markdown(hide_menu_style, unsafe_allow_html=True)

st.markdown('''
# **Sharp App**

 **SHARP App** creada en Streamlit usando la libreria  **pandas**.


---
''')

# Web App Title
st.markdown('''
# **Reporte Sharp App**
---
''')

# Upload CSV data
with st.sidebar.header('2. Carga el archivo Sharp con formato CSV'):
    uploaded_file = st.sidebar.file_uploader("Carga el archivo Sharp CSV", type=["csv"] )

# Pandas Profiling Report
if uploaded_file is not None:
    @st.cache_resource
    def load_csv():
        csv = pd.read_csv(uploaded_file, encoding='latin-1')
        return csv


    df_sharp = pd.DataFrame(load_csv(),
                            columns=['Código', 'Modelo', 'Fecha de registro', 'Fecha Asignado',
                                     'Fecha Reasignado',
                                     'Estado', 'Localización', 'Fecha de 1era Respuesta', 'Fecha firma solución',
                                     'Fecha firma cierre'])
    df_sharp['Tipo'] = df_sharp['Localización'].str[1:4]
    data = df_sharp.to_csv('Reporte Sharp.csv', encoding='utf8', index=False)
    st.header('Sharp DataFrame')
    st.dataframe(df_sharp)
    st.write('---')
    df_temp = df_sharp
    df_temp['Fecha Asignado'] = np.where(df_temp['Fecha Reasignado'].isnull(), df_temp['Fecha Asignado'],
                                         df_temp['Fecha Reasignado'])
    df_temp = df_temp.drop(['Fecha Reasignado'], axis=1)
    # Validacion 1er SLA REQ
    df_temp['Fecha de 1era Respuesta'] = pd.to_datetime(df_temp['Fecha de 1era Respuesta'], dayfirst=True)
    df_temp['Fecha Asignado'] = pd.to_datetime(df_temp['Fecha Asignado'], dayfirst=True)


    def rest_time(row):
        return row['Fecha de 1era Respuesta'] - row['Fecha Asignado']


    df_temp['Dif. Días 1era Respuesta'] = df_temp.apply(lambda r: rest_time(r), axis=1)
    holiday = ['2022-01-01', '2022-02-07', '2022-03-21', '2022-05-05', '2022-09-14', '2022-09-16', '2022-10-12', '2022-11-21']
    start = df_temp['Fecha de 1era Respuesta'].values.astype('datetime64[D]')
    end = df_temp['Fecha Asignado'].values.astype('datetime64[D]')
    # dias habiles solamente entre fecha Asignado y Fecha de 1era Respuesta
    
    days = np.busday_count(end, start, weekmask='Mon Tue Wed Thu Fri', holidays = holiday)

    df_temp['Dif. Días 1R'] = days - 1

    df_temp['Dias penalizables primera respuesta'] = df_temp['Dif. Días 1R'] + 2


    # Establecer las 19:00 del primer día

    def insert_time(row):
        return row['Fecha Asignado'].replace(hour=19, minute=0, second=0, microsecond=0)


    df_temp['Hora termino dia 1'] = df_temp.apply(lambda r: insert_time(r), axis=1)


    # Establecer las 08:00 del último día

    def insert_time2(row):
        return row['Fecha de 1era Respuesta'].replace(hour=8, minute=0, second=0, microsecond=0)


    df_temp['Hora inicio dia ultimo'] = df_temp.apply(lambda r: insert_time2(r), axis=1)

    # minutos del pimer día
    df_temp['Dif. Horas dia 1'] = df_temp.apply(
        lambda df_temp: (df_temp['Hora termino dia 1'] - df_temp['Fecha Asignado']), 1)

    df_temp['Dif. Horas (minutos) dia 1'] = df_temp['Dif. Horas dia 1'].dt.total_seconds() / 60

    df_temp['Dif. Horas (minutos) dia 1'] = np.where(df_temp['Dif. Horas (minutos) dia 1'] < 0, 0,
                                                     df_temp['Dif. Horas (minutos) dia 1'])

    # minutos del ultimo día
    df_temp['Dif. Horas (minutos) dia ultimo'] = df_temp.apply(
        lambda df_temp: (df_temp['Fecha de 1era Respuesta'] - df_temp['Hora inicio dia ultimo']), 1)

    df_temp['Dif. Horas (minutos) dia ultimo'] = df_temp['Dif. Horas (minutos) dia ultimo'].dt.total_seconds() / 60

    df_temp['Dif. Horas (minutos) dia ultimo'] = np.where(df_temp['Dif. Horas (minutos) dia ultimo'] < 0, 0,
                                                          df_temp['Dif. Horas (minutos) dia ultimo'])

    # minutos de los días de enmedio
    df_temp['Dif. Horas (minutos) dias adicionales'] = (660 * df_temp['Dif. Días 1R'])

    df_temp['Dif. Horas (minutos) dias adicionales'] = np.where(df_temp['Dif. Horas (minutos) dias adicionales'] < 0,
                                                                0, df_temp['Dif. Horas (minutos) dias adicionales'])

    # Tiempo tolerancia en Minutos
    df_temp['Tolerancia (minutos)'] = 120

    # Tiempo real de atención al usuario en Minutos
    df_temp['SLA TAU (Tiempo de Atención al Usuario, primera respuesta) Minutos'] = np.where(
        df_temp['Dif. Días 1R'] < 0, df_temp['Dif. Días 1era Respuesta'].dt.total_seconds() / 60, df_temp.apply(
            lambda df_temp: (
                    df_temp['Dif. Horas (minutos) dia 1'] + df_temp['Dif. Horas (minutos) dia ultimo']
                    + df_temp['Dif. Horas (minutos) dias adicionales']), 1)
    )

    # Tiempo real de atención al usuario en Minutos Temp
    df_temp['TA - Tolerancia (minutos)'] = np.where(
        df_temp['Dif. Días 1R'] < 0, df_temp['Dif. Días 1era Respuesta'].dt.total_seconds() / 60, df_temp.apply(
            lambda df_temp: (
                    df_temp['Dif. Horas (minutos) dia 1'] + df_temp['Dif. Horas (minutos) dia ultimo']
                    + df_temp['Dif. Horas (minutos) dias adicionales']), 1)
    )

    df_temp['TA - Tolerancia (minutos)'] = df_temp['TA - Tolerancia (minutos)'] - 120

    conditionlist = [
        (df_temp['TA - Tolerancia (minutos)'] <= 0),
        (df_temp['TA - Tolerancia (minutos)'] > 0)]
    choicelist = ['SI', 'NO']

    df_temp['Cumple 1er SLA'] = np.select(conditionlist, choicelist, default='Not Specified')

    df_temp['Dias penalizables primera respuesta'] = np.where(df_temp['Cumple 1er SLA'] == 'SI',
                                                              0, df_temp['Dias penalizables primera respuesta'])

    df_temp['Tolerancia (minutos)'] = df_temp['Tolerancia (minutos)'] / 60

    df_temp['SLA TAU (Tiempo de Atención al Usuario, primera respuesta) Minutos'] = df_temp[
                                                                                        'SLA TAU (Tiempo de Atención al Usuario, primera respuesta) Minutos'] / 60

    df_temp['TA - Tolerancia (minutos)'] = df_temp['TA - Tolerancia (minutos)'] / 60
    # Validacion Requerimientos 2do SLA

    in_SCJ = df_temp['Tipo'] == 'SCJ'

    df_sharpR = df_temp[in_SCJ]

    pd.options.mode.chained_assignment = None  # default='warn'

    df_sharpR['Fecha Asignado'] = pd.to_datetime(df_sharpR['Fecha Asignado'], dayfirst=True)
    df_sharpR['Fecha firma solución'] = pd.to_datetime(df_sharpR['Fecha firma solución'], dayfirst=True)

    df_sharpR['Dif. Días 2da Respuesta'] = df_sharpR.apply(
        lambda df_sharpR: (df_sharpR['Fecha firma solución'] - df_sharpR['Fecha Asignado']), 1)

    holiday = ['2022-01-01', '2022-02-07', '2022-03-21', '2022-05-05', '2022-09-14', '2022-09-16', '2022-10-12', '2022-11-21']

    start = df_sharpR['Fecha Asignado'].values.astype('datetime64[D]')
    end = df_sharpR['Fecha firma solución'].values.astype('datetime64[D]')

    # dias habiles solamente entre fecha Asignado y Fecha de 1era Respuesta
    days = np.busday_count(end, start, weekmask='Mon Tue Wed Thu Fri', holidays=holiday)

    df_sharpR['Dif. Días 2da'] = (days - 1) * -1


    # Establecer las 19:00 del primer día

    def insert_time(row):
        try:
            return row['Fecha Asignado'].replace(hour=19, minute=0, second=0, microsecond=0)
        except Exception as e:
                return print('insert_time:', e)


    df_sharpR['Hora termino dia 1'] = df_sharpR.apply(lambda r: insert_time(r), axis=1)


    # Establecer las 08:00 del último día

    def insert_time(row):
        return row['Fecha firma solución'].replace(hour=8, minute=0, second=0, microsecond=0)

    display(df_sharpR['Hora inicio dia ultimo'])
    df_sharpR['Hora inicio dia ultimo'] = df_sharpR.apply(lambda r: insert_time(r), axis=1)

    # minutos del pimer día
    df_sharpR['Dif. Horas dia 1 2da'] = df_sharpR.apply(
        lambda df_sharpR: (df_sharpR['Hora termino dia 1'] - df_sharpR['Fecha Asignado']), 1)

    df_sharpR['Dif. Horas (minutos) dia 1 2da'] = df_sharpR['Dif. Horas dia 1 2da'].dt.total_seconds() / 60

    df_sharpR['Dif. Horas (minutos) dia 1 2da'] = np.where(df_sharpR['Dif. Horas (minutos) dia 1 2da'] < 0, 0,
                                                           df_sharpR['Dif. Horas (minutos) dia 1 2da'])

    # minutos del ultimo día
    df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] = df_sharpR.apply(
        lambda df_sharpR: (df_sharpR['Fecha firma solución'] - df_sharpR['Hora inicio dia ultimo']), 1)

    df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] = df_sharpR[
                                                           'Dif. Horas (minutos) dia ultimo 2da'].dt.total_seconds() / 60

    df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] = np.where(df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] < 0, 0,
                                                                df_sharpR['Dif. Horas (minutos) dia ultimo 2da'])

    # minutos de los días de enmedio
    df_sharpR['Dif. Horas (minutos) dias adicionales 2da'] = (660 * (df_sharpR['Dif. Días 2da'] - 2))

    df_sharpR['Dif. Horas (minutos) dias adicionales 2da'] = np.where(
        df_sharpR['Dif. Horas (minutos) dias adicionales 2da'] < 0, 0,
        df_sharpR['Dif. Horas (minutos) dias adicionales 2da'])

    # Tiempo tolerancia en Minutos
    df_sharpR['Tolerancia 2do SLA (minutos)'] = np.where(
        df_sharpR['Localización'].str[1:4] == 'CCJ', 960, 480)

    # Tiempo real de atención al usuario en Minutos
    df_sharpR['SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] = np.where(
        df_sharpR['Dif. Días 2da'] < 2, df_sharpR['Dif. Días 2da Respuesta'].dt.total_seconds() / 60, df_sharpR.apply(
            lambda df_sharpR: (
                    df_sharpR['Dif. Horas (minutos) dia 1 2da'] + df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] +
                    df_sharpR['Dif. Horas (minutos) dias adicionales 2da']), 1)
    )

    # Tiempo real de atención al usuario en Minutos Temp
    df_sharpR['TA - Tolerancia 2do SLA (minutos)'] = np.where(
        df_sharpR['Dif. Días 2da'] < 2, df_sharpR['Dif. Días 2da Respuesta'].dt.total_seconds() / 60, df_sharpR.apply(
            lambda df_sharpR: (
                    df_sharpR['Dif. Horas (minutos) dia 1 2da'] + df_sharpR['Dif. Horas (minutos) dia ultimo 2da'] +
                    df_sharpR['Dif. Horas (minutos) dias adicionales 2da']), 1)
    )

    df_sharpR['TA - Tolerancia 2do SLA (minutos)'] = df_sharpR['TA - Tolerancia 2do SLA (minutos)'] - df_sharpR[
        'Tolerancia 2do SLA (minutos)']

    # Aqui comienza el calculo de la fecha límite de atención del ticket y el tiempo de tolerancia en días naturales.
    ccj = timedelta(days=0, seconds=0,
                    microseconds=0,
                    milliseconds=0,
                    minutes=960, hours=0)
    scjn = timedelta(days=0, seconds=0,
                     microseconds=0,
                     milliseconds=0,
                     minutes=7200, hours=0)
    # Seleccionar la tolerancia
    df_sharpR['tolerancia_min'] = np.where(df_sharpR['Localización'].str[1:4] == 'CCJ', 960, 480)


    def selector(row):
        dia = -1
        try:
            for d in range(6):
                if (row['tolerancia_min'] <= 0) & (row['tolerancia_min'] < 660):
                    break
                elif dia == -1:
                    dia = dia + 1
                    # print(dia)
                    if row['tolerancia_min'] <= row['Dif. Horas (minutos) dia 1 2da']:
                        row['Fecha límite de atención a ticket 2do nivel'] = row['Fecha Asignado'] + \
                                                                             timedelta(days=dia, seconds=0,
                                                                                       microseconds=0,
                                                                                       milliseconds=0, minutes=0,
                                                                                       hours=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + pd.to_timedelta(
                            row['tolerancia_min'], unit='m')
                        break
                    else:
                        row['tolerancia_min'] = row['tolerancia_min'] - row['Dif. Horas (minutos) dia 1 2da']
                else:
                    dia = dia + 1
                    # print(dia)
                    if row['tolerancia_min'] <= 660:
                        row['Fecha límite de atención a ticket 2do nivel'] = row['Fecha Asignado'].replace(hour=8,
                                                                                                           minute=0,
                                                                                                           second=0,
                                                                                                           microsecond=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + \
                                                                             timedelta(days=dia, seconds=0,
                                                                                       microseconds=0,
                                                                                       milliseconds=0, minutes=0,
                                                                                       hours=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + pd.to_timedelta(
                            row['tolerancia_min'], unit='m')
                        break
                    else:
                        row['tolerancia_min'] = row['tolerancia_min'] - 660
            return row['Fecha límite de atención a ticket 2do nivel']
        except Exception as e:
                return print('selector:', e)


    df_sharpR['Fecha límite de atención a ticket 2do nivel'] = df_sharpR.apply(lambda row: selector(row), axis=1)

    df_sharpR['Fecha límite de atención a ticket 2do nivel'] = pd.to_datetime(
        df_sharpR['Fecha límite de atención a ticket 2do nivel'], dayfirst=True)

    # Aqui termina el calculo de la nueva fecha de limite de atención del tickte y el tiempo de tolerancia en días
    # naturales.

    conditionlist = [
        (df_sharpR['TA - Tolerancia 2do SLA (minutos)'] <= 0),
        (df_sharpR['TA - Tolerancia 2do SLA (minutos)'] > 0)]
    choicelist = ['SI', 'NO']

    df_sharpR['Cumple 2do SLA'] = np.select(conditionlist, choicelist, default='Not Specified')

    df_sharpR['Tolerancia 2do SLA (minutos)'] = df_sharpR['Tolerancia 2do SLA (minutos)'] / 60

    df_sharpR['TA - Tolerancia 2do SLA (minutos)'] = df_sharpR['TA - Tolerancia 2do SLA (minutos)'] / 60

    df_sharpR['SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] = df_sharpR[
                                                                                              'SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] / 60

    # Validacion Incidencias 2do SLA

    in_CCJ = df_temp['Tipo'] == 'CCJ'

    df_sharpI = df_temp[in_CCJ]
    print('CCJ-Registros')
    display(df_sharpI)

    pd.options.mode.chained_assignment = None  # default='warn'

    df_sharpI['Fecha Asignado'] = pd.to_datetime(df_sharpI['Fecha Asignado'], dayfirst=True)
    df_sharpI['Fecha firma solución'] = pd.to_datetime(df_sharpI['Fecha firma solución'], dayfirst=True)

    df_sharpI['Dif. Días 2da Respuesta'] = df_sharpI.apply(
        lambda df_sharpI: (df_sharpI['Fecha firma solución'] - df_sharpI['Fecha Asignado']), 1)

    holiday = ['2022-01-01', '2022-02-07', '2022-03-21', '2022-05-05', '2022-09-14', '2022-09-16', '2022-10-12', '2022-11-21']

    start = df_sharpI['Fecha Asignado'].values.astype('datetime64[D]')
    end = df_sharpI['Fecha firma solución'].values.astype('datetime64[D]')

    # dias habiles solamente entre fecha Asignado y Fecha de 1era Respuesta
    days = np.busday_count(end, start, weekmask='Mon Tue Wed Thu Fri', holidays=holiday)

    df_sharpI['Dif. Días 2da'] = (days - 1) * -1


    # Establecer las 19:00 del primer día

    def insert_time(row):
        return row['Fecha Asignado'].replace(hour=19, minute=0, second=0, microsecond=0)

    display(df_sharpI['Hora termino dia 1'])
    df_sharpI['Hora termino dia 1'] = df_sharpI.apply(lambda r: insert_time(r), axis=1)


    # Establecer las 08:00 del último día

    def insert_time(row):
        return row['Fecha firma solución'].replace(hour=8, minute=0, second=0, microsecond=0)


    df_sharpI['Hora inicio dia ultimo'] = df_sharpI.apply(lambda r: insert_time(r), axis=1)

    # minutos del pimer día
    df_sharpI['Dif. Horas dia 1 2da'] = df_sharpI.apply(
        lambda df_sharpI: (df_sharpI['Hora termino dia 1'] - df_sharpI['Fecha Asignado']), 1)

    df_sharpI['Dif. Horas (minutos) dia 1 2da'] = df_sharpI['Dif. Horas dia 1 2da'].dt.total_seconds() / 60

    df_sharpI['Dif. Horas (minutos) dia 1 2da'] = np.where(df_sharpI['Dif. Horas (minutos) dia 1 2da'] < 0, 0,
                                                           df_sharpI['Dif. Horas (minutos) dia 1 2da'])

    # minutos del ultimo día
    df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] = df_sharpI.apply(
        lambda df_sharpI: (df_sharpI['Fecha firma solución'] - df_sharpI['Hora inicio dia ultimo']), 1)

    df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] = df_sharpI[
                                                           'Dif. Horas (minutos) dia ultimo 2da'].dt.total_seconds() / 60

    df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] = np.where(df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] < 0, 0,
                                                                df_sharpI['Dif. Horas (minutos) dia ultimo 2da'])

    # minutos de los días de enmedio
    df_sharpI['Dif. Horas (minutos) dias adicionales 2da'] = (660 * (df_sharpI['Dif. Días 2da'] - 2))

    df_sharpI['Dif. Horas (minutos) dias adicionales 2da'] = np.where(
        df_sharpI['Dif. Horas (minutos) dias adicionales 2da'] < 0, 0,
        df_sharpI['Dif. Horas (minutos) dias adicionales 2da'])

    # Tiempo tolerancia en Minutos
    df_sharpI['Tolerancia 2do SLA (minutos)'] = np.where(
        df_sharpI['Localización'].str[1:4] == 'CCJ', 960, 480)

    # Tiempo real de atención al usuario en Minutos
    df_sharpI['SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] = np.where(
        df_sharpI['Dif. Días 2da'] < 2, df_sharpI['Dif. Días 2da Respuesta'].dt.total_seconds() / 60, df_sharpI.apply(
            lambda df_sharpI: (
                    df_sharpI['Dif. Horas (minutos) dia 1 2da'] + df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] +
                    df_sharpI['Dif. Horas (minutos) dias adicionales 2da']), 1)
    )

    # Tiempo real de atención al usuario en Minutos Temp
    df_sharpI['TA - Tolerancia 2do SLA (minutos)'] = np.where(
        df_sharpI['Dif. Días 2da'] < 2, df_sharpI['Dif. Días 2da Respuesta'].dt.total_seconds() / 60, df_sharpI.apply(
            lambda df_sharpI: (
                    df_sharpI['Dif. Horas (minutos) dia 1 2da'] + df_sharpI['Dif. Horas (minutos) dia ultimo 2da'] +
                    df_sharpI['Dif. Horas (minutos) dias adicionales 2da']), 1)
    )

    df_sharpI['TA - Tolerancia 2do SLA (minutos)'] = df_sharpI['TA - Tolerancia 2do SLA (minutos)'] - df_sharpI[
        'Tolerancia 2do SLA (minutos)']

    # Aqui comienza el calculo de la fecha límite de atención del ticket y el tiempo de tolerancia en días naturales.
    ccj = timedelta(days=0, seconds=0,
                    microseconds=0,
                    milliseconds=0,
                    minutes=960, hours=0)
    scjn = timedelta(days=0, seconds=0,
                     microseconds=0,
                     milliseconds=0,
                     minutes=7200, hours=0)
    # Seleccionar la tolerancia
    df_sharpI['tolerancia_min'] = np.where(df_sharpI['Localización'].str[1:4] == 'CCJ', 960, 480)


    def selector(row):
        dia = -1
        try:
            for d in range(6):
                if (row['tolerancia_min'] <= 0) & (row['tolerancia_min'] < 660):
                    break
                elif dia == -1:
                    dia = dia + 1
                    # print(dia)
                    if row['tolerancia_min'] <= row['Dif. Horas (minutos) dia 1 2da']:
                        row['Fecha límite de atención a ticket 2do nivel'] = row['Fecha Asignado'] + \
                                                                             timedelta(days=dia, seconds=0,
                                                                                       microseconds=0,
                                                                                       milliseconds=0, minutes=0,
                                                                                       hours=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + pd.to_timedelta(
                            row['tolerancia_min'], unit='m')
                        break
                    else:
                        row['tolerancia_min'] = row['tolerancia_min'] - row['Dif. Horas (minutos) dia 1 2da']
                else:
                    dia = dia + 1
                    # print(dia)
                    if row['tolerancia_min'] <= 660:
                        row['Fecha límite de atención a ticket 2do nivel'] = row['Fecha Asignado'].replace(hour=8,
                                                                                                           minute=0,
                                                                                                           second=0,
                                                                                                           microsecond=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + \
                                                                             timedelta(days=dia, seconds=0,
                                                                                       microseconds=0,
                                                                                       milliseconds=0, minutes=0,
                                                                                       hours=0)
                        row['Fecha límite de atención a ticket 2do nivel'] = row[
                                                                                 'Fecha límite de atención a ticket 2do nivel'] + pd.to_timedelta(
                            row['tolerancia_min'], unit='m')
                        break
                    else:
                        row['tolerancia_min'] = row['tolerancia_min'] - 660
            return row['Fecha límite de atención a ticket 2do nivel']
        except Exception as e:
                return print('selector:', e)


    df_sharpI['Fecha límite de atención a ticket 2do nivel'] = df_sharpI.apply(lambda row: selector(row), axis=1)

    df_sharpI['Fecha límite de atención a ticket 2do nivel'] = pd.to_datetime(
        df_sharpI['Fecha límite de atención a ticket 2do nivel'], dayfirst=True)

    # Aqui termina el calculo de la fecha limite de atención del ticket y el tiempo de tolerancia en días naturales.

    conditionlist = [
        (df_sharpI['TA - Tolerancia 2do SLA (minutos)'] <= 0),
        (df_sharpI['TA - Tolerancia 2do SLA (minutos)'] > 0)]
    choicelist = ['SI', 'NO']

    df_sharpI['Cumple 2do SLA'] = np.select(conditionlist, choicelist, default='Not Specified')

    df_sharpI['Tolerancia 2do SLA (minutos)'] = df_sharpI['Tolerancia 2do SLA (minutos)'] / 60

    df_sharpI['TA - Tolerancia 2do SLA (minutos)'] = df_sharpI['TA - Tolerancia 2do SLA (minutos)'] / 60

    df_sharpI['SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] = df_sharpI[
                                                                                              'SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA'] / 60

    df_result = pd.merge(df_sharpI, df_sharpR, how='outer')

    df_result = df_result.drop(
        ['Tipo', 'Hora termino dia 1', 'Hora inicio dia ultimo', 'Dif. Horas dia 1', 'Dif. Horas (minutos) dia 1',
         'Dif. Horas (minutos) dia ultimo', 'Dif. Horas (minutos) dias adicionales', 'Dif. Días 1era Respuesta',
         'Dif. Días 1R', 'Dif. Días 2da Respuesta', 'Dif. Días 2da', 'Dif. Horas dia 1 2da',
         'Dif. Horas (minutos) dia 1 2da', 'Dif. Horas (minutos) dia ultimo 2da',
         'Dif. Horas (minutos) dias adicionales 2da'], axis='columns')
    # Obtiene las filas para los cuales las columnas Cumple 1er SLA y Cumple 2do SLA tienen el valor: SI
    indexNames = df_result[(df_result['Cumple 1er SLA'] == 'SI') & (df_result['Cumple 2do SLA'] == 'SI')].index
    # Borra estas columnas del dataFrame
    df_result.drop(indexNames, inplace=True)
    st.header('Reporte Final Sharp')

    def color_df(val):
        if val == 'SI':
            color = 'green'
        else:
            color = 'red'
        return f'background-color: {color}'


    st.dataframe(df_result.style.applymap(color_df, subset=['Cumple 1er SLA', 'Cumple 2do SLA']))
    file_name = 'Reporte Final Sharp.csv'
    csv_exp = df_result.to_csv(data)
    if csv_exp is not None:
        b64 = base64.b64encode(csv_exp.encode()).decode()  # some strings <-> bytes conversions necessary here
        href = f'<a href="data:file/csv;base64,{b64}" download="{file_name}" > Download Reporte Final Sharp  (CSV) </a>'
        st.markdown(href, unsafe_allow_html=True)
    st.write('---')
    st.header('Reporte Penalizacion Sharp')
    df_penalizacion = df_result.copy()
    df_penalizacion = df_penalizacion.rename(columns={'Nombre': 'Usuario'})
    conditionlist = [
        (df_penalizacion['Modelo'] == 'MXB450P'),
        (df_penalizacion['Modelo'] == 'MXC304W'),
        (df_penalizacion['Modelo'] == 'MXB476W'),
        (df_penalizacion['Modelo'] == 'MXM1205'),
        (df_penalizacion['Modelo'] == 'MXM5071'),
        (df_penalizacion['Modelo'] == 'PLOTTER HP'),
        (df_penalizacion['Modelo'] == 'ESCANER HP')]
    choicelist = [670, 902, 700, 7585, 1968, 6500, 12800]

    df_penalizacion['Costo mensual equipo'] = np.select(conditionlist, choicelist, default='Not Specified')


    def calcula_pena1(row):
        monto = 0
        if (row['Cumple 1er SLA'] == 'NO') & (row['Dias penalizables primera respuesta'] >= 1):
            monto = (float(row['Costo mensual equipo']) * 0.03289474) * float(
                row['Dias penalizables primera respuesta'])
            # print(monto)
        else:
            monto = 0

        return round(monto, 2)


    df_penalizacion['Penalizacion 1era respuesta'] = df_penalizacion.apply(lambda r: calcula_pena1(r), axis=1)


    def calcula_pena2(row):
        monto = 0
        if row['Cumple 2do SLA'] == 'NO':
            monto = (float(row['Costo mensual equipo']) * 0.01)
            # print(monto)
        else:
            monto = 0

        return round(monto, 2)


    df_penalizacion['Penalizacion 2da respuesta'] = df_penalizacion.apply(lambda r: calcula_pena2(r), axis=1)

    df_penalizacion['Sumatoria Penalizacion 1era y 2da respuesta'] = df_penalizacion.apply(lambda df_penalizacion: (
            df_penalizacion['Penalizacion 1era respuesta'] + df_penalizacion['Penalizacion 2da respuesta']), 1)


    def calcula_penaFinal(row):
        monto = 0
        try:
            if row['Sumatoria Penalizacion 1era y 2da respuesta'] > (0.02 * float(row['Costo mensual equipo'])):
                monto = round((0.02 * float(row['Costo mensual equipo'])), 2)
                # print(monto)
            else:
                monto = row['Sumatoria Penalizacion 1era y 2da respuesta']
        except:
            print('')

        return round(monto, 2)


    df_penalizacion['Total Final Penalizacion'] = df_penalizacion.apply(lambda r: calcula_penaFinal(r), axis=1)
    del (df_penalizacion['Modelo'])
    del (df_penalizacion['Estado'])
    del (df_penalizacion['Fecha firma cierre'])
    del (df_penalizacion['tolerancia_min'])
    df_penalizacion = df_penalizacion.rename(
        columns={'Código': 'Número de incidente / requerimiento',
                 'Fecha de registro': 'Fecha de registro incidente / requerimiento',
                 'Fecha de 1era Respuesta': 'Fecha de primera respuesta',
                 'Tolerancia (minutos)': 'Tolerancia primera respuesta (horas)',
                 'TA - Tolerancia (minutos)': 'Tiempo de Atención - Tolerancia de primera respuesta (horas)',
                 'SLA TAU (Tiempo de Atención al Usuario, primera respuesta) Minutos': 'Tiempo de atención total primera respuesta 1er SLA  (horas).',
                 'SLA TAU (Tiempo de Atención al Usuario, 2da respuesta) Minutos 2do SLA': 'Tiempo de atención total segunda respuesta  (horas). Horario Laboral',
                 'Tolerancia 2do SLA (minutos)': 'Tiempo de tolerancia resolución 2do. SLA (horas)',
                 'TA - Tolerancia 2do SLA (minutos)': 'Tiempo de atención total - Tolerancia (2do SLA) (horas)',
                 'Penalizacion 1era respuesta': 'Costo total penalizacion 1era respuesta.',
                 'Penalizacion 2da respuesta': 'Costo total penalizacion 2da respuesta - Reporte Automático.',
                 'Sumatoria Penalizacion 1era y 2da respuesta': 'Costo total sumatoria penalizacion primera respuesta y segunda respuesta.'})
    df_penalizacion = df_penalizacion.reindex(
        columns=['Número de incidente / requerimiento', 'Fecha de registro incidente / requerimiento',
                 'Fecha Asignado', 'Fecha de primera respuesta', 'Localización',
                 'Tolerancia primera respuesta (horas)',
                 'Tiempo de atención total primera respuesta 1er SLA  (horas).',
                 'Tiempo de Atención - Tolerancia de primera respuesta (horas)',
                 'Cumple 1er SLA',
                 'Tiempo de tolerancia resolución 2do. SLA (horas)',
                 'Tiempo de atención total segunda respuesta  (horas). Horario Laboral',
                 'Tiempo de atención total - Tolerancia (2do SLA) (horas)',
                 'Cumple 2do SLA',
                 'Fecha límite de atención a ticket 2do nivel',
                 'Fecha firma solución',
                 'Costo mensual equipo',
                 'Costo total penalizacion 1era respuesta.',
                 'Costo total penalizacion 2da respuesta - Reporte Automático.',
                 'Costo total sumatoria penalizacion primera respuesta y segunda respuesta.',
                 'Total Final Penalizacion'])
    # del (df_penalizacion['Horas penalizables '])
    print(df_penalizacion['Total Final Penalizacion'])
    # Obtiene las filas para las cuales la columna Total Final Penalizacion tiene el valor 0
    indexNames = df_penalizacion[df_penalizacion['Total Final Penalizacion'] == 0.00].index
    # Borra estas columnas del dataFrame
    df_penalizacion.drop(indexNames, inplace=True)

    file_name = 'Reporte Penalizacion Sharp.csv'
    st.dataframe(df_penalizacion)
    csv_exp = df_penalizacion.to_csv(data, index=False)
    b64 = base64.b64encode(csv_exp.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{file_name}" ' \
           f'> Download Reporte Penalizacion Sharp  (CSV) </a>'
    st.markdown(href, unsafe_allow_html=True)

    st.write('---')

    st.header('Sharp Graficos')
    df_new = df_result.copy()
    # df_new = df_new.rename_axis('Tipo de incidencia')
    options = st.multiselect(
        'Escoge un SLA', ['Cumple 1er SLA', 'Cumple 2do SLA'], ['Cumple 1er SLA']
    )
    if not options:
        st.error("Por favor selecciona un tipo de SLA.")
    if options == ['Cumple 2do SLA', 'Cumple 1er SLA a la vez']:
        st.error("Por favor selecciona solo un tipo de SLA.")
    if options == ['Cumple 1er SLA']:
        data = df_new.groupby(['Cumple 1er SLA']).size()
        if hasattr(data, 'SI') & hasattr(data, 'NO'):
            df = pd.DataFrame({'SI': {'Cumple 1er SLA': data.SI}, 'NO': {'Cumple 1er SLA': data.NO}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 1er SLA",
                              xTitle='Cumple 1er SLA - No / Si', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            df_new['Porcentajes'] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            respuestas = [Si_No.SI, Si_No.NO]
            tipo = ['SI', 'NO']
            explode = [0.2, 0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 1er SLA - TECPLUSS %')
            # st.table(Si_No)
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
            df_new["porcentajes"] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            fig3 = df_new["Cumple 1er SLA"].iplot(kind="histogram", bins=20, theme="white", title="Cumple 1er SLA",
                                                  xTitle='Cumple 1er SLA - No / Si', yTitle='Count', asFigure=True)
        elif hasattr(data, 'SI'):
            df = pd.DataFrame({'SI': {'Cumple 1er SLA': data.SI}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 1er SLA",
                              xTitle='Cumple 1er SLA - Si', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            df_new['Porcentajes'] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            respuestas = [Si_No.SI]
            tipo = ['SI']
            explode = [0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 1er SLA - TECPLUSS %')
            # st.table(Si_No)
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
            df_new["porcentajes"] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            fig3 = df_new["Cumple 1er SLA"].iplot(kind="histogram", bins=20, theme="white", title="Cumple 1er SLA",
                                                  xTitle='Cumple 1er SLA - Si', yTitle='Count', asFigure=True)
        elif hasattr(data, 'NO'):
            df = pd.DataFrame({'NO': {'Cumple 1er SLA': data.NO}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 1er SLA",
                              xTitle='Cumple 1er SLA - NO', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            df_new['Porcentajes'] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            respuestas = [Si_No.NO]
            tipo = ['NO']
            explode = [0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 1er SLA - TECPLUSS %')
            # st.table(Si_No)
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
            df_new["porcentajes"] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            fig3 = df_new["Cumple 1er SLA"].iplot(kind="histogram", bins=20, theme="white", title="Cumple 1er SLA",
                                                  xTitle='Cumple 1er SLA - No', yTitle='Count', asFigure=True)


    if options == ['Cumple 2do SLA']:
        data = df_new.groupby(['Cumple 2do SLA']).size()
        print(data)
        if hasattr(data, 'SI') & hasattr(data, 'NO'):
            df = pd.DataFrame({'SI': {'Cumple 2do SLA': data.SI}, 'NO': {'Cumple 2do SLA': data.NO}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 2do SLA",
                              xTitle='Cumple 2do SLA - No / Si', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            df_new["porcentajes"] = (df_new.groupby('Cumple 1er SLA').size() / df_new['Cumple 1er SLA'].count()) * 100
            fig3 = df_new["Cumple 1er SLA"].iplot(kind="histogram", bins=20, theme="white", title="Cumple 1er SLA",
                                                  xTitle='Cumple 1er SLA - No / Si', yTitle='Count', asFigure=True)
            st.write('---')
            df_new['Porcentajes'] = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            respuestas = [Si_No.SI, Si_No.NO]
            tipo = ['SI', 'NO']
            explode = [0.2, 0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 2do SLA - TECPLUSS %')
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
        elif hasattr(data, 'SI'):
            df = pd.DataFrame({'SI': {'Cumple 2do SLA': data.SI}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 2do SLA",
                              xTitle='Cumple 2do SLA - Si', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            st.write('---')
            df_new['Porcentajes'] = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            respuestas = [Si_No.SI]
            tipo = ['SI']
            explode = [0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 2do SLA - TECPLUSS %')
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
        elif hasattr(data, 'NO'):
            df = pd.DataFrame({'NO': {'Cumple 2do SLA': data.NO}})
            st.write(df)
            figura = df.iplot(kind="bar", bins=20, theme="white", title="Cumple 2do SLA",
                              xTitle='Cumple 2do SLA - Si', yTitle='Count', asFigure=True)
            st.plotly_chart(figura)
            st.write('---')
            df_new['Porcentajes'] = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            Si_No = (df_new.groupby('Cumple 2do SLA').size() / df_new['Cumple 2do SLA'].count()) * 100
            respuestas = [Si_No.SI]
            tipo = ['NO']
            explode = [0]  # Destacar algunos
            fig, ax = plt.subplots()
            ax.pie(respuestas, labels=tipo, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
            st.title('Cumple 2do SLA - TECPLUSS %')
            st.pyplot(fig)
            png_exp = plt.savefig('Grafica Pie Si-No.jpeg')
            st.write('---')
