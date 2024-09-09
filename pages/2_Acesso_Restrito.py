import pickle
from pathlib import Path
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import base64

import streamlit_authenticator as stauth
import pandas as pd

st.set_page_config(
    page_title="I TAÇA DAS SOCIEDADES",
    page_icon=":trophy:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.logo('logo_sds/CONDEB PAG 1.png')

names = ["Master","SDUFRJ","Hermenêutica","SdDUFC","SDS","Senatus","GDO","SDP","SdDUFSC"]
usernames = ["master","sdufrj","hermeneutica","sddufc","sds","senatus","gdo","sdp","sddufsc"]

file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

credentials = {"usernames":{}}

for un, name, pw in zip(usernames, names, hashed_passwords):
    user_dict = {"name":name,"password":pw}
    credentials["usernames"].update({un:user_dict})

authenticator = stauth.Authenticate(credentials, 'sd_dashboard', 'auth', cookie_expiry_days=30)

name, authentication_status, username = authenticator.login()

if authentication_status == False:
    st.error("Usuário/senha inválidos")

if authentication_status == None:
    st.warning("Por favor, faça o login")

if authentication_status:
    st.write('# PAINEL DA I TAÇA DAS SOCIEDADES')
    st.write('### Confira o andamento da maior competição entre as Sociedades de Debates do Brasil!')
    st.sidebar.caption('Login como: ' + name)
    st.divider()

    #Conexão com o sheets
    conn = st.connection('gsheets', type=GSheetsConnection)

    #Bases utilizadas
    delegacoes = conn.read(worksheet='TdS_Delegações', usecols = list(range(2)), ttl=5).dropna(how='all')
    rodadas = conn.read(worksheet='TdS_Rodadas', usecols = list(range(6)), ttl=5).dropna(how='all')
    resultados = conn.read(worksheet='TdS_Resultados', usecols = list(range(8)), ttl=5).dropna(how='all')
    juizes = conn.read(worksheet='TdS_Juizes', usecols = list(range(5)), ttl=5).dropna(how='all')
    temporario_rodada = conn.read(worksheet='TdS_Suporte', usecols = list(range(6)), ttl=5).dropna(how='all')

    #Lista de equipes
    lista_rodadas = rodadas['Rodada'].unique()
    sds = delegacoes['instituicao'].unique()
    sds = pd.DataFrame(sds, columns=['Instituição'])
    imagens_sds = ['logo_sds/sdufrj.jpeg', 'logo_sds/gdo.jpeg','logo_sds/sddufc.jpeg','logo_sds/sds.jpeg'
                   ,'logo_sds/sddufsc.jpeg','logo_sds/hermeneutica.jpeg','logo_sds/senatus.jpeg','logo_sds/sdp.jpeg']
    sds['Equipe'] = imagens_sds
    sds.set_index('Instituição', inplace=True)
    sds["Pontos"] = 0
    sds["N de Primeiros"] = 0
    sds["Total Sps"] = 0
    sds['Juizes Enviados'] = 0

    juizes['Juiz_cargo'] = juizes['Juiz'] + juizes['Posição']
    juizes['Juizes'] = juizes[['Rodada','Sala','Juiz_cargo']].groupby(['Rodada','Sala'])['Juiz_cargo'].transform(lambda x: ','.join(x))
    juizes_sintetico = juizes.drop(columns=['Juiz','Posição','Juiz_cargo'])
    juizes_sintetico = juizes[['Rodada','Sala','Juizes']].drop_duplicates().reset_index(drop=True).set_index('Rodada')

    partidas_agregado = resultados[['Rodada','Sala','Instituição','Casa','Classificação','Sps']].groupby(['Rodada','Sala','Instituição','Casa']).agg({'Classificação':'max', 'Sps':'sum'}).reset_index()
    tabela_partidas = partidas_agregado.pivot(index=['Rodada', 'Sala'], columns='Casa', values='Instituição').reset_index()
    tabela_partidas = tabela_partidas[['Rodada','Sala','1° GOVERNO','1ª OPOSIÇÃO','2° GOVERNO','2ª OPOSIÇÃO']].set_index('Rodada')
    tabela_resultado = partidas_agregado.pivot(index='Instituição', columns='Rodada', values='Classificação').reset_index('Instituição')

    base_resultados = partidas_agregado.copy()
    base_resultados['Resultado'] = base_resultados['Instituição'] + ' - ' + base_resultados['Classificação'].astype(str)
    base_resultados = base_resultados.pivot(index=['Rodada','Sala'], columns='Casa', values='Resultado').reset_index()
    base_resultados = pd.merge(base_resultados, juizes_sintetico, on=['Sala','Rodada'], how='left').reset_index(drop=True).set_index('Rodada')
    base_resultados = base_resultados[['Sala','1° GOVERNO','1ª OPOSIÇÃO','2° GOVERNO','2ª OPOSIÇÃO','Juizes']]
    rodada_corrente = resultados[resultados['Classificação'].isnull()]['Rodada'].reset_index(drop=True)[0]
    data_rodada_corrente = rodadas[rodadas['Rodada'] == rodada_corrente]['Data'].reset_index(drop=True)[0]
    base_resultados = base_resultados[base_resultados['Juizes'].notna()]

    juizes_rodada = rodadas[rodadas["Rodada"] == int(rodada_corrente)]['Escalação Juízes'].reset_index(drop=True)[0]
    juizes_rodada = juizes_rodada.split('; ')
    juizes_rodada = pd.DataFrame(juizes_rodada, columns=['Juizes'])

    #----------- DEFINIÇÃO DE DELEGAÇÃO DO LOGIN ----------------

    if name != 'Master':
        debatedores = delegacoes[delegacoes['instituicao'] == name]['Nome']

    for index, row in partidas_agregado.iterrows():
        equipe = row['Instituição']
        resultado = row['Classificação']
        sds.loc[equipe, 'Total Sps'] += row['Sps']
        if resultado == '1°':
            sds.loc[equipe, 'Pontos'] += 3
            sds.loc[equipe, 'N de Primeiros'] += 1
        elif resultado == '2°':
            sds.loc[equipe, 'Pontos'] += 2
        elif resultado == '3°':
            sds.loc[equipe, 'Pontos'] += 1
        elif resultado == '4°':
            sds.loc[equipe, 'Pontos'] += 0

    for indez, row in juizes.iterrows():
        equipe = row['SD']
        if equipe != 'Condeb':
            sds.loc[equipe, 'Juizes Enviados'] += 1

    sds.sort_values(['Pontos', 'N de Primeiros', 'Total Sps'], ascending=[False, False, False], inplace=True)
    sds.reset_index(inplace=True)
    sds.index += 1
    sds['Colocação'] = sds.index
    sds.set_index('Colocação', inplace=True)

    #----------- ATUALIZAÇÃO DE DEBATEDOR DA PARTIDA ----------------

    if name == 'Master':
        st.sidebar.write('### Aconpanhamento de inscrições: Rodada ' + str(int(rodada_corrente)) + '(' + str(data_rodada_corrente) + ')')
        st.sidebar.dataframe(temporario_rodada[temporario_rodada['rodada'] == int(rodada_corrente)])
        falta_escalacao = sds[~sds['Instituição'].isin(temporario_rodada[temporario_rodada['rodada'] == int(rodada_corrente)]['delegação'].unique())]
        if not falta_escalacao.empty:
            st.sidebar.warning('### Atenção! As seguintes equipes ainda não escalaram seus debatedores:' + str(falta_escalacao['Instituição'].values.tolist()))
        else:
            escalacao_completa = temporario_rodada[temporario_rodada['rodada'] == int(rodada_corrente)]
            debatedores_rodada = pd.concat([escalacao_completa[['delegação','membro 1']], escalacao_completa[['delegação','membro 2']]])
            debatedores_rodada['membro 1'].fillna(debatedores_rodada['membro 2'], inplace=True)
            debatedores_rodada = debatedores_rodada[['delegação','membro 1']].rename(columns={'membro 1':'Nome'})


            st.sidebar.markdown('### Alocação de Juízes')
            with st.form(key='alocacao_form'):
                with st.sidebar:
                    chair_sala_1 = st.text_input('Chair Sala 1')
                    chair_sala_2 = st.text_input('Chair Sala 2')
                    juiz_sala_1 = st.multiselect('Juiz Sala 1', escalacao_completa[escalacao_completa['juiz'].notnull()]['juiz'].unique())
                    juiz_sala_2 = st.multiselect('Juiz Sala 2', escalacao_completa[escalacao_completa['juiz'].notnull()]['juiz'].unique())
                    cadastrar_aloc = st.form_submit_button(label = "Alocar Juízes")

            if cadastrar_aloc:
                if not chair_sala_1 or not chair_sala_2 or not juiz_sala_1 or not juiz_sala_2:
                    st.warning("Por favor, preencha todos os campos para seguir com Cadastro")
                    st.stop()
                else:
                    # Create a new dataframe
                    alocacao = pd.DataFrame(columns=["Rodada", "Sala", "Juiz", "Posição", "SD"])

                    # Fill the dataframe based on the given rules
                    alocacao = alocacao.append({"Rodada": int(rodada_corrente), "Sala": 1, "Juiz": chair_sala_1, "Posição": "(c)", "SD": "Condeb"}, ignore_index=True)
                    alocacao = alocacao.append({"Rodada": int(rodada_corrente), "Sala": 2, "Juiz": chair_sala_2, "Posição": "(c)", "SD": "Condeb"}, ignore_index=True)
                    for juiz in juiz_sala_1:
                        alocacao = alocacao.append({"Rodada": int(rodada_corrente), "Sala": 1, "Juiz": juiz, "Posição": "(w)", "SD": escalacao_completa.loc[escalacao_completa["juiz"] == juiz, "delegação"].values[0]}, ignore_index=True)
                    for juiz in juiz_sala_2:
                        alocacao = alocacao.append({"Rodada": int(rodada_corrente), "Sala": 2, "Juiz": juiz, "Posição": "(w)", "SD": escalacao_completa.loc[escalacao_completa["juiz"] == juiz, "delegação"].values[0]}, ignore_index=True)
                    alocacao['Juiz_cargo'] = alocacao['Juiz'] + alocacao['Posição']
                    alocacao['Juizes'] = alocacao[['Rodada','Sala','Juiz_cargo']].groupby(['Rodada','Sala'])['Juiz_cargo'].transform(lambda x: ','.join(x))
                    updated_df = pd.concat([juizes, alocacao], ignore_index=True)
                    conn.update(worksheet='TdS_Juizes', data=updated_df)
                    st.sidebar.success('Escalação Cadastrada!')
            st.markdown('### DRAW DA RODADA: ' + str(int(rodada_corrente)) + '(' + str(data_rodada_corrente) + ')')

            draw_rodada = base_resultados[base_resultados.index == int(rodada_corrente)].replace(' - nan', '', regex=True)
            draw_rodada

            resultado_rodada = resultados[resultados['Rodada'] == int(rodada_corrente)]

    #----------------- RESULTADOS SALA 1 -------------------#
            with st.form(key='resultado_sala1_form'):
                st.markdown('### INPUT DE RESULTADO DA SALA 1: ' + str(int(rodada_corrente)) + '(' + str(data_rodada_corrente) + ')')
                col30, col31 = st.columns(2)
                with col30:
                    st.markdown('#### 1° GOVERNO: ' + str(draw_rodada['1° GOVERNO'].values[0]))
                    col40, col41 = st.columns(2)
                    with col40:
                        primeiro_ministro1 = st.selectbox('Primeiro Ministro', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1° GOVERNO'].values[0]]['Nome'], index=None)
                        adjunto_pm1 = st.selectbox('Vice Primeiro Ministro', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1° GOVERNO'].values[0]]['Nome'], index=None)
                    with col41:
                        sps_pm1 = st.number_input('Sps PM', min_value=50, max_value=100, step=1)
                        sps_vpm1 = st.number_input('Sps VPM', min_value=50, max_value=100, step=1)
                    st.markdown('#### 2° GOVERNO: ' + str(draw_rodada['2° GOVERNO'].values[0]))
                    col50, col51 = st.columns(2)
                    with col50:
                        ext_gov1 = st.selectbox('Membro do Governo',debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2° GOVERNO'].values[0]]['Nome'], index=None)
                        wp_gov1 = st.selectbox('Whip do Governo', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2° GOVERNO'].values[0]]['Nome'], index=None)
                    with col51:
                        sps_ext_gov1 = st.number_input('Sps MG', min_value=50, max_value=100, step=1)
                        sps_wp_gov1 = st.number_input('Sps WPG', min_value=50, max_value=100, step=1)

                with col31:
                    st.markdown('#### 1ª OPOSIÇÃO: ' + str(draw_rodada['1ª OPOSIÇÃO'].values[0]))
                    col60, col61 = st.columns(2)
                    with col60:
                        lider_oposicao1 = st.selectbox('Líder da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[0]]['Nome'], index=None)
                        adjunto_oposicao1 = st.selectbox('Vice líder da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[0]]['Nome'], index=None)
                    with col61:
                        sps_lo1 = st.number_input('Sps LO', min_value=50, max_value=100, step=1)
                        sps_vlo1 = st.number_input('Sps VLO', min_value=50, max_value=100, step=1)
                    st.markdown('#### 2ª OPOSIÇÃO: ' + str(draw_rodada['2ª OPOSIÇÃO'].values[0]))
                    col70, col71 = st.columns(2)
                    with col70:
                        ext_op1 = st.selectbox('Membro da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[0]]['Nome'], index=None)
                        wp_op1 = st.selectbox('Whip da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[0]]['Nome'], index=None)
                    with col71:
                        sps_ext_op1 = st.number_input('Sps MO', min_value=50, max_value=100, step=1)
                        sps_wp_op1 = st.number_input('Sps WPO', min_value=50, max_value=100, step=1)
                resultado_sala1 = st.form_submit_button('Montar resultado Prelilminar da Sala 1')

            if resultado_sala1:
                st.session_state.show_confirmation = True
            
            if st.session_state.get('show_confirmation', False):
                st.warning('Resultado Preliminar Sala 1')
                call_sala_1 = pd.DataFrame(columns=['Posição','Delegação', 'Soma sps'])
                call_sala_1 = call_sala_1.append({'Posição':'1° GOVERNO','Delegação': draw_rodada['1° GOVERNO'].values[0], 'Soma sps': sps_pm1 + sps_vpm1}, ignore_index=True)
                call_sala_1 = call_sala_1.append({'Posição':'1ª OPOSIÇÃO','Delegação': draw_rodada['1ª OPOSIÇÃO'].values[0], 'Soma sps': sps_lo1 + sps_vlo1}, ignore_index=True)
                call_sala_1 = call_sala_1.append({'Posição':'2° GOVERNO','Delegação': draw_rodada['2° GOVERNO'].values[0], 'Soma sps': sps_ext_gov1 + sps_wp_gov1}, ignore_index=True)
                call_sala_1 = call_sala_1.append({'Posição':'2ª OPOSIÇÃO','Delegação': draw_rodada['2ª OPOSIÇÃO'].values[0], 'Soma sps': sps_ext_op1 + sps_wp_op1}, ignore_index=True)
                call_sala_1['Colocação'] = call_sala_1['Soma sps'].rank(ascending=False)
                call_sala_1 = call_sala_1.sort_values('Colocação').set_index('Colocação')
                call_sala_1
                confirm1 = st.button('Confirmar Resultado Sala 1')
                if confirm1:
                    input_resultado_sala_1 = pd.DataFrame(columns=['Rodada','Sala','Instituição','Debatedor','Casa','Posição','Classificação','Sps'])
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['1° GOVERNO'].values[0], 'Debatedor': primeiro_ministro1, 'Casa': '1° GOVERNO', 'Posição': 'PM', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['1° GOVERNO'].values[0]].index[0])) + '°', 'Sps': sps_pm1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['1° GOVERNO'].values[0], 'Debatedor': adjunto_pm1, 'Casa': '1° GOVERNO', 'Posição': 'VPM', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['1° GOVERNO'].values[0]].index[0])) + '°', 'Sps': sps_vpm1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['1ª OPOSIÇÃO'].values[0], 'Debatedor': lider_oposicao1, 'Casa': '1ª OPOSIÇÃO', 'Posição': 'LO', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[0]].index[0])) + '°', 'Sps': sps_lo1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['1ª OPOSIÇÃO'].values[0], 'Debatedor': adjunto_oposicao1, 'Casa': '1ª OPOSIÇÃO', 'Posição': 'VLO', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[0]].index[0])) + '°', 'Sps': sps_vlo1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['2° GOVERNO'].values[0], 'Debatedor': ext_gov1, 'Casa': '2° GOVERNO', 'Posição': 'MG', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['2° GOVERNO'].values[0]].index[0])) + '°', 'Sps': sps_ext_gov1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['2° GOVERNO'].values[0], 'Debatedor': wp_gov1, 'Casa': '2° GOVERNO', 'Posição': 'WG', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['2° GOVERNO'].values[0]].index[0])) + '°', 'Sps': sps_wp_gov1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['2ª OPOSIÇÃO'].values[0], 'Debatedor': ext_op1, 'Casa': '2ª OPOSIÇÃO', 'Posição': 'MO', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[0]].index[0])) + '°', 'Sps': sps_ext_op1}, ignore_index=True)
                    input_resultado_sala_1 = input_resultado_sala_1.append({'Rodada': int(rodada_corrente), 'Sala': 1, 'Instituição': draw_rodada['2ª OPOSIÇÃO'].values[0], 'Debatedor': wp_op1, 'Casa': '2ª OPOSIÇÃO', 'Posição': 'WO', 'Classificação': str(int(call_sala_1[call_sala_1['Delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[0]].index[0])) + '°', 'Sps': sps_wp_op1}, ignore_index=True)
                    resultado_sala_1 = resultados[(resultados['Rodada'] == int(rodada_corrente)) & (resultados['Sala']==1)]
                    input_resultado_sala_1 = input_resultado_sala_1.set_index(resultado_sala_1.index)
                    resultado_sala_1.update(input_resultado_sala_1)
                    resultados.update(resultado_sala_1)
                    conn.update(worksheet='TdS_Resultados', data=resultados)
                    st.success('Resultado da Sala 1 Salvo!')
                st.divider()

        #----------------- RESULTADOS SALA 2 -------------------#
            with st.form(key='resultado_sala2_form'):
                st.markdown('### INPUT DE RESULTADO DA SALA 2: ' + str(int(rodada_corrente)) + '(' + str(data_rodada_corrente) + ')')
                col80, col81 = st.columns(2)
                with col80:
                    st.markdown('#### 1° GOVERNO: ' + str(draw_rodada['1° GOVERNO'].values[1]))
                    col90, col91 = st.columns(2)
                    with col90:
                        primeiro_ministro = st.selectbox('Primeiro Ministro', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1° GOVERNO'].values[1]]['Nome'], index=None)
                        adjunto_pm = st.selectbox('Vice Primeiro Ministro', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1° GOVERNO'].values[1]]['Nome'], index=None)
                    with col91:
                        sps_pm = st.number_input('Sps PM', min_value=50, max_value=100, step=1)
                        sps_vpm = st.number_input('Sps VPM', min_value=50, max_value=100, step=1)
                    st.markdown('#### 2° GOVERNO: ' + str(draw_rodada['2° GOVERNO'].values[1]))
                    col100, col101 = st.columns(2)
                    with col100:
                        ext_gov = st.selectbox('Membro do Governo',debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2° GOVERNO'].values[1]]['Nome'], index=None)
                        wp_gov = st.selectbox('Whip do Governo', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2° GOVERNO'].values[1]]['Nome'], index=None)
                    with col101:
                        sps_ext_gov = st.number_input('Sps MG', min_value=50, max_value=100, step=1)
                        sps_wp_gov = st.number_input('Sps WPG', min_value=50, max_value=100, step=1)

                with col81:
                    st.markdown('#### 1ª OPOSIÇÃO: ' + str(draw_rodada['1ª OPOSIÇÃO'].values[1]))
                    col110, col111 = st.columns(2)
                    with col110:
                        lider_oposicao = st.selectbox('Líder da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[1]]['Nome'], index=None)
                        adjunto_oposicao = st.selectbox('Vice líder da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[1]]['Nome'], index=None)
                    with col111:
                        sps_lo = st.number_input('Sps LO', min_value=50, max_value=100, step=1)
                        sps_vlo = st.number_input('Sps VLO', min_value=50, max_value=100, step=1)
                    st.markdown('#### 2ª OPOSIÇÃO: ' + str(draw_rodada['2ª OPOSIÇÃO'].values[1]))
                    col120, col121 = st.columns(2)
                    with col120:
                        ext_op = st.selectbox('Membro da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[1]]['Nome'], index=None)
                        wp_op = st.selectbox('Whip da Oposição', debatedores_rodada[debatedores_rodada['delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[1]]['Nome'], index=None)
                    with col121:
                        sps_ext_op = st.number_input('Sps MO', min_value=50, max_value=100, step=1)
                        sps_wp_op = st.number_input('Sps WPO', min_value=50, max_value=100, step=1)
                resultado_sala2 = st.form_submit_button('Montar resultado Prelilminar da Sala 2')

            if resultado_sala2:
                st.session_state.show_confirmation = True
            
            if st.session_state.get('show_confirmation', False):
                st.warning('Resultado Preliminar Sala 2')
                call_sala_2 = pd.DataFrame(columns=['Posição','Delegação', 'Soma sps'])
                call_sala_2 = call_sala_2.append({'Posição':'1° GOVERNO','Delegação': draw_rodada['1° GOVERNO'].values[1], 'Soma sps': sps_pm + sps_vpm}, ignore_index=True)
                call_sala_2 = call_sala_2.append({'Posição':'1ª OPOSIÇÃO','Delegação': draw_rodada['1ª OPOSIÇÃO'].values[1], 'Soma sps': sps_lo + sps_vlo}, ignore_index=True)
                call_sala_2 = call_sala_2.append({'Posição':'2° GOVERNO','Delegação': draw_rodada['2° GOVERNO'].values[1], 'Soma sps': sps_ext_gov + sps_wp_gov}, ignore_index=True)
                call_sala_2 = call_sala_2.append({'Posição':'2ª OPOSIÇÃO','Delegação': draw_rodada['2ª OPOSIÇÃO'].values[1], 'Soma sps': sps_ext_op + sps_wp_op}, ignore_index=True)
                call_sala_2['Colocação'] = call_sala_2['Soma sps'].rank(ascending=False)
                call_sala_2 = call_sala_2.sort_values('Colocação').set_index('Colocação')
                call_sala_2
                confirm2 = st.button('Confirmar Resultado Sala 2')
                if confirm2:
                    input_resultado_sala_2 = pd.DataFrame(columns=['Rodada','Sala','Instituição','Debatedor','Casa','Posição','Classificação','Sps'])
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['1° GOVERNO'].values[1], 'Debatedor': primeiro_ministro, 'Casa': '1° GOVERNO', 'Posição': 'PM', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['1° GOVERNO'].values[1]].index[0])) + '°', 'Sps': sps_pm}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['1° GOVERNO'].values[1], 'Debatedor': adjunto_pm, 'Casa': '1° GOVERNO', 'Posição': 'VPM', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['1° GOVERNO'].values[1]].index[0])) + '°', 'Sps': sps_vpm}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['1ª OPOSIÇÃO'].values[1], 'Debatedor': lider_oposicao, 'Casa': '1ª OPOSIÇÃO', 'Posição': 'LO', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[1]].index[0])) + '°', 'Sps': sps_lo}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['1ª OPOSIÇÃO'].values[1], 'Debatedor': adjunto_oposicao, 'Casa': '1ª OPOSIÇÃO', 'Posição': 'VLO', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['1ª OPOSIÇÃO'].values[1]].index[0])) + '°', 'Sps': sps_vlo}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['2° GOVERNO'].values[1], 'Debatedor': ext_gov, 'Casa': '2° GOVERNO', 'Posição': 'MG', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['2° GOVERNO'].values[1]].index[0])) + '°', 'Sps': sps_ext_gov}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['2° GOVERNO'].values[1], 'Debatedor': wp_gov, 'Casa': '2° GOVERNO', 'Posição': 'WG', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['2° GOVERNO'].values[1]].index[0])) + '°', 'Sps': sps_wp_gov}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['2ª OPOSIÇÃO'].values[1], 'Debatedor': ext_op, 'Casa': '2ª OPOSIÇÃO', 'Posição': 'MO', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[1]].index[0])) + '°', 'Sps': sps_ext_op}, ignore_index=True)
                    input_resultado_sala_2 = input_resultado_sala_2.append({'Rodada': int(rodada_corrente), 'Sala': 2, 'Instituição': draw_rodada['2ª OPOSIÇÃO'].values[1], 'Debatedor': wp_op, 'Casa': '2ª OPOSIÇÃO', 'Posição': 'WO', 'Classificação': str(int(call_sala_2[call_sala_2['Delegação'] == draw_rodada['2ª OPOSIÇÃO'].values[1]].index[0])) + '°', 'Sps': sps_wp_op}, ignore_index=True)
                    resultado_sala_2 = resultados[(resultados['Rodada'] == int(rodada_corrente)) & (resultados['Sala']==2)]
                    input_resultado_sala_2 = input_resultado_sala_2.set_index(resultado_sala_2.index)
                    resultado_sala_2.update(input_resultado_sala_2)
                    resultados.update(resultado_sala_2)
                    conn.update(worksheet='TdS_Resultados', data=resultados)
                    st.success('Resultado da Sala 2 Salvo!')
                st.divider()



    else:
        st.sidebar.write('### Escalação de Equipe (Rodada ' + str(int(rodada_corrente)) + ')')

        with st.form(key="escalacao_form"):
            with st.sidebar:
                debatedor_1 = st.sidebar.selectbox('Debatedor 1', debatedores, index=None)
                debatedor_2 = st.sidebar.selectbox('Debatedor 2', debatedores, index=None)
                if juizes_rodada[juizes_rodada['Juizes'] == str(name)].empty:
                    st.sidebar.caption('### SD não escalada para enviar juiz para esta rodada')
                    juiz = ''
                    email_juiz = ''
                else:
                    juiz = st.sidebar.text_input('Juiz Representante')
                    email_juiz = st.sidebar.text_input('Email do Juiz')
                cadastrar = st.form_submit_button(label = "Cadastrar")
        if cadastrar:
            if not debatedor_1 or not debatedor_2:
                st.warning("Por favor, preencha todos os campos para seguir com Cadastro")
                st.stop()
            else:
                cadastro_rodada = pd.DataFrame([
                    {
                        'rodada': int(rodada_corrente),
                        'delegação': name,
                        'membro 1': debatedor_1,
                        'membro 2': debatedor_2,
                        'juiz': juiz,
                        'e-mail juiz':email_juiz
                    }
                ]
                )
                updated_df = pd.concat([temporario_rodada, cadastro_rodada], ignore_index=True)
                conn.update(worksheet='TdS_Suporte', data=updated_df)
                st.sidebar.success('Escalação Cadastrada!')

    def open_image(path: str):
        with open(path, "rb") as p:
            file = p.read()
            return f"data:image/png;base64,{base64.b64encode(file).decode()}"


    sds["Equipe"] = sds.apply(lambda x: open_image(x['Equipe']), axis=1)
    sds = sds[['Equipe','Instituição','Pontos','N de Primeiros','Total Sps','Juizes Enviados']]


    st.write('### TABELA DA COMPETIÇÃO')
    st.dataframe(sds,
                    column_config={
                        "Total Sps": st.column_config.ProgressColumn('Total Sps', format="%d", min_value=0, max_value=str(sds['Total Sps'].max())),
                        "Equipe":st.column_config.ImageColumn()
                    })

    st.divider()

    col1, col2, col10 = st.columns(3)
    with col1:
        st.write('### CHAVEAMENTO')
        tabela_partidas

    with col2:
        st.write('#### Próxima Rodada: ' + str(int(rodada_corrente)) + '(' + str(data_rodada_corrente) + ')')
        tabela_rodada = tabela_partidas.loc[rodada_corrente]
        tabela_rodada = tabela_rodada.set_index('Sala')
        tabela_rodada = tabela_rodada[['1° GOVERNO','1ª OPOSIÇÃO','2° GOVERNO','2ª OPOSIÇÃO']]
        tabela_rodada
        st.write('##### Escalação de Juízes: ' + str(juizes_rodada['Juizes'].to_list()).replace('[','').replace(']','').replace("'",''))

    with col10:
        st.write('### CALENDARIO')
        calendario = rodadas[['Rodada','Data','Horário','Escalação Juízes']].set_index('Rodada')
        calendario

    
    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        st.write('### RESULTADOS GERAIS')
        base_resultados

    with col4:
        st.write('### RESULTADOS POR RODADA')
        tabela_resultado = tabela_resultado.set_index('Instituição')
        tabela_resultado

    st.sidebar.write('### Dowload Resultados')
    st.dowload_button(
        label='Resultado Rodada',
        data= resultados.to_csv(index=False),
        file_name='Resultados.csv',
        mime='text/csv'
    )

    st.dowload_button(
        label='Resultado Juízes',
        data= juizes.to_csv(index=False),
        file_name='juizes.csv',
        mime='text/csv'
    )

    authenticator.logout('Logout','sidebar')