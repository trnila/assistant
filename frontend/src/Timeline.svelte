<script>
    export let data;
    export let last_fetch;
    export let fetch_count;

    let max = Math.max(...data.map((r) => r.elapsed));
</script>

<div class="container">
    <h2>Processing time</h2>
    <dl>
        <dt>Last fetch</dt>
        <dd>{new window.Date(last_fetch * 1000).toLocaleString("cs")}</dd>
        <dt>Count</dt>
        <dd>{fetch_count}</dd>
    </dl>
    {#each data as restaurant}
        <div style="width: {(restaurant.elapsed / max) * 100}%;">
            ({restaurant.elapsed.toFixed(3)} s)
            <strong>{restaurant.name}</strong>
        </div>
    {/each}
</div>

<style>
    dl {
        margin: 0;
    }

    dt:after {
        content: ":";
    }

    dt,
    dd {
        display: inline;
        margin: 0;
    }

    dd {
        margin-inline-start: 5px;
    }

    dd:after {
        display: block;
        content: "";
    }

    dt {
        font-weight: bold;
    }

    .container {
        width: 100%;
        max-width: 600px;
        margin-bottom: 5px;
    }
    div div {
        background: lightblue;
        white-space: nowrap;
    }
    h2 {
        margin: 0;
    }
</style>
