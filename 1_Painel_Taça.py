import pickle
from pathlib import Path
import streamlit as st
import pandas as pd
import base64

st.set_page_config(
    page_title="I TAÇA DAS SOCIEDADES",
    page_icon=":trophy:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.logo('logo_sds/CONDEB PAG 1.png')

st.write('# PAINEL DA I TAÇA DAS SOCIEDADES')
st.write('### Confira o andamento da maior competição entre as Sociedades de Debates do Brasil!')
st.divider()

#Bases utilizadas
delegacoes = pd.read_csv('data/Registro_CNDC - TdS_Delegações.csv')
rodadas = pd.read_csv('data/Registro_CNDC - TdS_Rodadas.csv')
resultados = pd.read_csv('data/Registro_CNDC - TdS_Resultados.csv')
juizes = pd.read_csv('data/Registro_CNDC - TdS_Juizes.csv')

#Base de moções
mocoes = rodadas[rodadas['Moção'] != '-'][['Rodada','Moção','Info']].set_index('Rodada')

#Lista de equipes
lista_rodadas = rodadas['Rodada'].unique()
sds = delegacoes['instituicao'].unique()
sds = pd.DataFrame(sds, columns=['Instituição'])
imagens_sds = ['logo_sds/sdufrj.jpeg', 'logo_sds/gdo.jpeg','logo_sds/sddufc.jpeg','logo_sds/sds.jpeg'
                ,'logo_sds/sddufsc.jpeg','logo_sds/hermeneutica.jpeg','logo_sds/senatus.jpeg','logo_sds/sdp.jpeg']
sds[' '] = imagens_sds
sds.set_index('Instituição', inplace=True)
sds["Pontos"] = 0
sds["N de Primeiros"] = 0
sds["Total Sps"] = 0
sds['Juizes Enviados'] = 0

spks = resultados[resultados['Classificação'].notna()]
spks_rodada = spks.pivot(index='Debatedor', columns='Rodada', values='Sps').reset_index()

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

def open_image(path: str):
    with open(path, "rb") as p:
        file = p.read()
        return f"data:image/png;base64,{base64.b64encode(file).decode()}"


sds[" "] = sds.apply(lambda x: open_image(x[' ']), axis=1)
sds = sds[[' ','Instituição','Pontos','N de Primeiros','Total Sps','Juizes Enviados']]


st.write('### TABELA DA COMPETIÇÃO')
st.dataframe(sds,
                column_config={
                    "Total Sps": st.column_config.ProgressColumn('Total Sps', format="%d", min_value=0, max_value=str(sds['Total Sps'].max())),
                    " ":st.column_config.ImageColumn()
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

st.divider()

col7, col8 = st.columns(2)



with col7:
    st.write('### TABELA DE DEBATEDORES')
    delegacoes = delegacoes.rename(columns={'Nome':'Debatedor'})
    delegacoes = delegacoes.merge(spks_rodada, on='Debatedor', how='left')
    delegacoes.set_index('Debatedor', inplace=True)
    delegacoes['Número de Participações'] = resultados['Debatedor'].value_counts()
    delegacoes['Média de Sps'] = resultados[['Debatedor','Sps']].groupby('Debatedor').mean()
    delegacoes['Total Sps'] = resultados[['Debatedor','Sps']].groupby('Debatedor').sum()
    delegacoes.sort_values('Total Sps', ascending=False, inplace=True)
    delegacoes
with col8:
    st.write('### MOÇÕES DEBATIDAS')
    mocoes
