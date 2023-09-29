<script>
    export let data;
    export let last_fetch;
    export let fetch_count;
    export let first_access;
    export let access_count;

    let max = Math.max(...data.map((r) => r.elapsed));
</script>

<div class="container">
    <h2>Stats for nerds</h2>
    <dl>
        <dt>First access</dt>
        <dd>{new window.Date(first_access * 1000).toLocaleString("cs")}</dd>

        <dt>Access count</dt>
        <dd>{access_count}</dd>

        <dt>Last fetch</dt>
        <dd>{new window.Date(last_fetch * 1000).toLocaleString("cs")}</dd>

        <dt>Fetch count</dt>
        <dd>{fetch_count}</dd>
    </dl>
    {#each data as restaurant}
        <div style="width: {(restaurant.elapsed / max) * 100}%;" class="timeline">
            ({restaurant.elapsed.toFixed(3)} s)
            <strong>{restaurant.name}</strong>
        </div>
    {/each}
</div>

<style>
    dl {
        margin: 0;
        margin-bottom: 2px;
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
    .timeline {
        background: lightblue;
        white-space: nowrap;
    }

    :global(body.dark .timeline) {
      background: #add8e636;
    }

    h2 {
        margin: 0;
    }
</style>
