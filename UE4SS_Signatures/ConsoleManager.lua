-- Atomic Heart (UE 4.27, AtomicHeart-Win64-Shipping.exe de 09/10/2026)
-- O scan padrao do UE4SS achava 2 candidatos (RVA 0x2422BB0 e 0x3651A20).
-- O correto e 0x2422BB0: e o getter do singleton do console
-- ("se ConsoleManagerSingleton for nulo, cria; devolve"), chamado de 8994 lugares.
-- O outro candidato nao tem nenhuma chamada direta.
-- Este padrao aparece uma unica vez no executavel. Se o jogo atualizar, pode deixar de bater.
function Register()
    return "48 83 EC 38 48 83 3D ?? ?? ?? ?? 00 0F 85 ?? ?? ?? ?? 48 8B 0D"
end

function OnMatchFound(MatchAddress)
    return MatchAddress
end
