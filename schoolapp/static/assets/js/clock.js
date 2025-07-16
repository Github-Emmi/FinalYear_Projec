document.addEventListener("DOMContentLoaded", () => {
  const HOURHAND = document.querySelector("#hour");
  const MINUTEHAND = document.querySelector("#minute");
  const SECONDHAND = document.querySelector("#second");

  function runTheClock() {
    const now = new Date();
    const hr = now.getHours();
    const min = now.getMinutes();
    const sec = now.getSeconds();

    const hrPos = (hr % 12) * 30 + min * 0.5;
    const minPos = min * 6 + sec * 0.1;
    const secPos = sec * 6;

    HOURHAND.style.transform = `rotate(${hrPos}deg)`;
    MINUTEHAND.style.transform = `rotate(${minPos}deg)`;
    SECONDHAND.style.transform = `rotate(${secPos}deg)`;
  }

  runTheClock();
  setInterval(runTheClock, 1000);
});
