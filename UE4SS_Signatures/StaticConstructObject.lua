-- Atomic Heart (UE 4.27, AtomicHeart-Win64-Shipping.exe de 09/10/2026)
-- O scan padrao do UE4SS achava 2 candidatos (RVA 0xEBA7A0 e 0x276E4C0).
-- O correto e 0x276E4C0: funcao grande (0x19F bytes, frame de 0x1A0) chamada de
-- 902 lugares, no mesmo modulo CoreUObject de FUObjectHashTables::Get.
-- O outro candidato e um wrapper pequeno (0x87 bytes).
-- Este padrao aparece uma unica vez no executavel. Se o jogo atualizar, pode deixar de bater.
function Register()
    return "48 89 5C 24 10 48 89 6C 24 18 48 89 74 24 20 57 41 56 41 57 48 81 EC A0 01 00 00 48"
end

function OnMatchFound(MatchAddress)
    return MatchAddress
end
