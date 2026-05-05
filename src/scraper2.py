import re
import pandas as pd
from playwright.sync_api import sync_playwright
from datetime import datetime

ciudad_pattern = re.compile(
    r"\b([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+(?:\s+(?:de|del|la|las|los|el)\s+)?"
    r"(?:[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]+)*)\b"
)

metadata_tokens = (
    "hace ",
    "postúlate",
    "salario",
    "contrato",
    "jornada",
    "experiencia",
)


def clean_text(value):
    if not value:
        return None
    return " ".join(value.split())


def extract_title(oferta):
    try:
        text = oferta.locator("h2 a.js-o-link").first.text_content()
        return clean_text(text) or "Titulo no encontrado"
    except Exception:
        return "Titulo no encontrado"


def extract_company(oferta):
    try:
        company = oferta.locator("a[offer-grid-article-company-url]").first.text_content()
        company = clean_text(company)
        if company:
            return company
    except Exception:
        pass

    try:
        important = oferta.locator('p:has-text("importante empresa")')
        if important.count() > 0:
            return "Importante empresa del sector"
    except Exception:
        pass

    return "Empresa no encontrada"


def extract_location(oferta):
    try:
        spans = oferta.locator("p.fs16.fc_base.mt5 span").all()
        for span in spans:
            text = clean_text(span.text_content())
            if not text:
                continue

            lowered = text.lower()
            if any(token in lowered for token in metadata_tokens):
                continue

            if ciudad_pattern.search(text):
                return text
    except Exception:
        pass

    return "No especificada"

def extract_link(oferta):
    """Extrae el link a la oferta completa."""
    try:
        link_elem = oferta.locator("h2 a.js-o-link")
        href = link_elem.get_attribute("href")
        if href:
            return f"https://ar.computrabajo.com{href}"
    except Exception:
        pass
    return "No disponible"

def extract_modalidad(oferta):
    """Extrae la modalidad (presencial/remoto/híbrido)."""
    try:
        modalidad = oferta.locator(".icon.i_home_office").first
        if modalidad.count() == 0:

            modalidad = oferta.locator(".icon.i_home").first
        
        if modalidad.count() > 0:

            return "Remoto/Híbrido"
    except Exception:
        pass
    return "No especificada"

def extract_salary(oferta):
    try:
        salary_elem = oferta.locator(".icon.i_salary").first
        if salary_elem.count() > 0:
            salary = oferta.locator(".dIB.mr10").first.text_content()
            salary = clean_text(salary)
            return salary 
    except Exception:
        pass
    return "No especificado"

def scrape_ofertas():
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://ar.computrabajo.com/empleos-de-data")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)


        # contamos la cantidad de paginas
        # try:
        #     total_texto = page.locator(".title_page .fwB").text_content()
        #     total_ofertas = int(total_texto.strip())
        # except Exception:
        #     total_ofertas = 0

        # if total_ofertas > 0:
        #     ofertas_por_pagina = 20
        #     total_paginas = (total_ofertas + ofertas_por_pagina - 1) // ofertas_por_pagina
        # else:
        total_paginas = 2


        datos = []
        for pagina in range(1,total_paginas + 1):
            url = f"https://ar.computrabajo.com/empleos-de-data?p={pagina}"
            print(f"Pagina {pagina}...")
            
            page.goto(url)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            ofertas = page.locator(".box_offer").all()
            print(f"Encontré {len(ofertas)} ofertas\n")
            
            for oferta in ofertas[:20]:
                titulo = extract_title(oferta)
                empresa = extract_company(oferta)
                ubicacion = extract_location(oferta)
                salario = extract_salary(oferta)
                modalidad = extract_modalidad(oferta)
                link = extract_link(oferta)
                datos.append(
                    {
                        "Titulo": titulo,
                        "Empresa": empresa,
                        "Ubicacion": ubicacion,
                        "Salario": salario,
                        "Modalidad": modalidad,
                        "Link": link,
                    }
                )

        if datos:
            df = pd.DataFrame(datos)
            nombre = f"ofertas_data_{datetime.now():%Y-%m-%d}.csv"
            df.to_csv(f"data/raw/{nombre}", index=False)
            print(f"Guardado en data/raw/{nombre} ({len(df)} ofertas)")
        else:
            print("No se encontraron ofertas para exportar.")

        browser.close()


if __name__ == "__main__":
    scrape_ofertas()
