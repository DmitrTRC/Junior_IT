let message = "Hello, World!";

console.log(message);

let chislo = 7
let ochki = 0

for (let i = 1; i <= 5; i++) {
    let otvet = Number(prompt(chislo + " × " + i + " = ?"))
    if (otvet === chislo * i) {
        console.log("✅ Верно!")
        ochki = ochki + 1
    } else {
        console.log("❌ Мимо. Правильно: " + (chislo * i))
    }
}

console.log("Очки: " + ochki + " из 5")
