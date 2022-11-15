<script>
    import { onMount, onDestroy } from "svelte";
    import { Fireworks } from "fireworks-js";

    let container;
    let fireworks;
    let stopTimer;

    onMount(() => {
        fireworks = new Fireworks(container);
        fireworks.start();
        stopTimer = setTimeout(cancel, 5000);
    });

    onDestroy(() => {
        clearInterval(stopTimer);
        fireworks?.stop(true);
    });

    function cancel() {
        fireworks?.waitStop(true);
        fireworks = null;
        clearInterval(stopTimer);
    }
</script>

<svelte:window on:keydown={(evt) => evt.key == 'Escape' && cancel()} on:click={cancel} />

<div bind:this={container} />

<style>
    div {
        top: 0;
        left: 0;
        position: fixed;
        width: 100%;
        height: 100%;
        pointer-events: none;
    }
</style>
