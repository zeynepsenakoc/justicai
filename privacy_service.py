import re
import logging

logger = logging.getLogger(__name__)

class PrivacyManager:
    def __init__(self):
      
        self.patterns = {
            "TCKN": r'\b[1-9]{1}[0-9]{9}[02468]{1}\b',  
            "PHONE": r'(?:\+90|0)?5\d{2}[ .]?\d{3}[ .]?\d{2}[ .]?\d{2}', 
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
            "IBAN": r'TR\d{2}\s?(\d{4}\s?){5}\d{2}' 
        }

    def anonymize(self, text):
        """
        Metindeki hassas verileri bulur ve maskeler.
        Dönüş: (maskelenmis_metin, veri_haritasi)
        """
        if not text:
            return text, {}

        mapping = {} 
        masked_text = text

    
        tckn_matches = re.findall(self.patterns["TCKN"], masked_text)
        for i, match in enumerate(set(tckn_matches)): 
            placeholder = f"[KVKK_TCKN_{i+1}]"
            mapping[placeholder] = match
            masked_text = masked_text.replace(match, placeholder)


        phone_matches = re.findall(self.patterns["PHONE"], masked_text)
        for i, match in enumerate(set(phone_matches)):
            placeholder = f"[KVKK_TEL_{i+1}]"
            mapping[placeholder] = match
            masked_text = masked_text.replace(match, placeholder)

      
        email_matches = re.findall(self.patterns["EMAIL"], masked_text)
        for i, match in enumerate(set(email_matches)):
            placeholder = f"[KVKK_EMAIL_{i+1}]"
            mapping[placeholder] = match
            masked_text = masked_text.replace(match, placeholder)

        
        iban_matches = re.findall(self.patterns["IBAN"], masked_text)
        for i, match in enumerate(set(iban_matches)):
            placeholder = f"[KVKK_IBAN_{i+1}]"
            mapping[placeholder] = match
            masked_text = masked_text.replace(match, placeholder)

        if mapping:
            logger.info(f"🛡️ GİZLİLİK KATMANI: {len(mapping)} adet hassas veri maskelendi.")

        return masked_text, mapping

    def de_anonymize(self, masked_text, mapping):
        """
        Yapay zekadan gelen cevaptaki maskeleri orijinal verilerle değiştirir.
        (Dilekçenin son halinde verilerin geri gelmesi için)
        """
        if not mapping or not masked_text:
            return masked_text
        
        final_text = masked_text
        for placeholder, original in mapping.items():
            final_text = final_text.replace(placeholder, original)
        
        return final_text


privacy_guard = PrivacyManager()