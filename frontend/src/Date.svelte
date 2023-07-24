<style>
    h1 {
        margin: 0;
        white-space: nowrap;
    }
</style>

<script>
    const days = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ];

    let date = new Date();
    let day = days[date.getDay()];
    let counter = null;

    function remainingMillis() {
        const target = new Date();
        target.setHours(11, 0, 0, 0);
        //target.setHours(19, 44, 0, 0);
        return target - new Date();
    }

    function remaining() {
        let diff = remainingMillis();
        if (diff <= 0) {
            return null;
        }
        const hours = parseInt(diff / 3600000);
        diff -= hours * 3600000;
        const minutes = parseInt(diff / 60000);
        diff -= minutes * 60000;
        const secs = parseInt(diff / 1000);
        diff -= secs * 1000;
        return {
            hours,
            minutes,
            secs,
            milliseconds: diff,
        };
    }

    setInterval(() => {
        const r = remaining();
        if (r) {
            counter = `${r.hours}:${("00" + r.minutes).substr(
                -2
            )}:${("00" + r.secs).substr(-2)}.${("000" + r.milliseconds).substr(
                -3
            )}`;
        } else {
            counter = null;
        }
    }, 21);


    let alarm;
    if(remainingMillis() > 0) {
        setTimeout(function() {
            alarm.volume = 0.3;
            alarm.play();
        }, remainingMillis())
    }
</script>

<h1>
    {day}
    {date.getDate()}. {date.getMonth() + 1}
    {#if counter}
    - {counter}
    {/if}
</h1>

<audio bind:this={alarm} src="https://trnila.eu/rooster.mp3"></audio>

