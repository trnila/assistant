<script>
    export let data;

    let max = Math.max(...data.map((r) => r.elapsed));
</script>

<div class="container">
    <h2>Processing time</h2>
    {#each data as restaurant}
        <div style="width: {(restaurant.elapsed / max) * 100}%;">
            ({restaurant.elapsed.toFixed(3)} s)
            <strong>{restaurant.name}</strong>
        </div>
    {/each}
</div>

<style>
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
