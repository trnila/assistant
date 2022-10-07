<style>
    h1 {
        margin: 0;
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

    function remaining() {
        const target = new Date();
        target.setHours(11, 0, 0, 0);
        //target.setHours(23, 59, 0, 0);

        let diff = target - new Date();
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
</script>

<h1>
    {day}
    {date.getDate()}. {date.getMonth() + 1}
    {#if counter}
    - {counter}
    {/if}
</h1>
